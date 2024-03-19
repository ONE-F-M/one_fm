import frappe, json
import datetime
from frappe import _
import pandas as pd
from frappe.workflow.doctype.workflow_action.workflow_action import (
    get_common_email_args, deduplicate_actions, get_next_possible_transitions,
    get_doc_workflow_state, get_workflow_name, get_users_next_action_data
)
from frappe.utils import getdate, today, cstr, add_to_date, nowdate, add_days
from frappe.model.workflow import apply_workflow
from one_fm.utils import (workflow_approve_reject, send_workflow_action_email)
from one_fm.api.notification import create_notification_log, get_employee_user_id
from one_fm.api.doc_events import get_employee_user_id
from frappe.desk.form.assign_to import add as add_assignment, DuplicateToDoError

class OverlappingShiftError(frappe.ValidationError):
    pass

def validate(doc, event=None):
    # ensure status is not pending
    if doc.is_new():
        doc.status='Draft'
    if doc.status=='Pending Approval':
        doc.status == 'Draft'
    if doc.status == 'Draft' and doc.purpose == 'Assign Unrostered Employee':
        if check_for_roster(doc):
            frappe.throw("Employee Already has been rostered for the given dates")
    process_shift_assignemnt(doc) # set shift assignment and employee schedule

def shift_request_submit(self):
    if self.workflow_state != 'Update Request':
        self.db_set("status", self.workflow_state) if self.workflow_state!='Pending Approval' else self.db_set("status", 'Draft')

def validate_default_shift(self):
    default_shift = frappe.get_value("Employee", self.employee, "default_shift")
    if self.shift_type == default_shift:
        pass

def on_update(doc, event):
    if doc.workflow_state in ['Approved', 'Rejected']:
        workflow_approve_reject(doc, [get_employee_user_id(doc.employee)])

    if doc.workflow_state == 'Draft':
        send_workflow_action_email(doc,[doc.approver])
        validate_shift_overlap(doc)
    if doc.workflow_state == 'Pending Approval':
        assign_approver(doc, doc.approver)


def assign_approver(doc, approver_id):
    add_assignment({
				'doctype': doc.doctype,
				'name': doc.name,
				'assign_to': [approver_id],
				'description':
				_(
					f"""
						Please Note that a Shift Request {doc.name} has been submitted.<br>
						Please review and take necessary actions
					"""
				)
			})

def validate_shift_overlap(doc):
    curr_date = getdate()
    shift_assignment = frappe.db.get_list("Shift Assignment", {'employee':doc.employee, 'start_date': doc.from_date, "roster_type": "Basic", 'status':'Active'}, ['shift','start_datetime', 'end_datetime'])
    shift_type = frappe.db.get_list("Shift Type",{'name':doc.shift_type}, ['start_time', 'end_time'])

    shift_start_time = datetime.datetime.combine(curr_date , (datetime.datetime.min + shift_type[0].start_time).time())
    if shift_type[0].start_time > shift_type[0].end_time:
        shift_end_time = datetime.datetime.combine(add_to_date(curr_date, days=1) , (datetime.datetime.min + shift_type[0].end_time).time())
    else:
        shift_end_time = datetime.datetime.combine(curr_date , (datetime.datetime.min + shift_type[0].end_time).time())

    if doc.roster_type == "Over-Time" and shift_assignment:
        if shift_start_time < shift_assignment[0].end_datetime:
            msg = _(
                "Employee {0} already has an Basic Shift {1} that overlaps within this period."
            ).format(
                frappe.bold(doc.employee),
                frappe.bold(shift_assignment[0].shift),
            )
            frappe.throw(msg, title=_("Overlapping Shifts"), exc=OverlappingShiftError)

def shift_request_cancel(self):
    '''
        Method used to override Shift Request on_cancel
    '''
    cancel_shift_assignment_of_request(self)

def on_update_after_submit(doc, method):
    if doc.update_request:
        if doc.workflow_state == 'Update Request':
            doc.db_set("status", 'Draft')
            cancel_shift_assignment_of_request(doc)

def process_shift_assignemnt(doc, event=None):
    role_abbr = frappe.db.get_value("Operations Role",doc.operations_role,'post_abbrv')
    shift_worker = frappe.db.get_value("Employee", doc.employee, 'shift_working')
    if doc.workflow_state=='Approved' and doc.docstatus==1:
        if doc.assign_day_off == 1:
            assign_day_off(doc)
        elif doc.purpose == 'Replace Existing Assignment':
            if doc.roster_type == "Basic" and cstr(doc.from_date) <= cstr(getdate()) <= cstr(doc.to_date):
                shift_assignemnt = frappe.get_list("Shift Assignment", filters = [['employee','=', doc.employee], ['start_date', 'between', [doc.from_date, doc.to_date]], ['roster_type','=',"Basic"]], fields=['name'])
                if shift_assignemnt:
                    replace_shift_assignment(shift_assignemnt[0].name, doc)
                if shift_worker == 1:
                    # check for existing schedule
                    schedule_date_range = [str(i.date()) for i in pd.date_range(start=doc.from_date, end=doc.to_date)]
                    existing_schedules = frappe.db.sql(f""" SELECT name, date FROM `tabEmployee Schedule`
                        WHERE employee="{doc.employee}" AND roster_type="{doc.roster_type}"
                        AND date BETWEEN '{doc.from_date}' AND '{doc.to_date}' """, as_dict=1)
                    if existing_schedules:
                        replace_employee_schedule(doc, existing_schedules, schedule_date_range)
        elif doc.purpose == 'Assign Unrostered Employee':
            create_shift_assignment_from_request(doc)
            schedule_date_range = [str(i.date()) for i in pd.date_range(start=doc.from_date, end=doc.to_date)]
            new_date_range = [i for i in schedule_date_range]
            if new_date_range:
                for date in new_date_range:
                    create_employee_schedule_from_request(doc, date)
        elif doc.purpose == 'Update Existing Assignment':
            if check_for_roster(doc):
                if doc.roster_type == "Basic" and cstr(doc.from_date) <= cstr(getdate()) <= cstr(doc.to_date):
                    shift_assignemnt = frappe.get_list("Shift Assignment", filters = [['employee','=', doc.employee], ['start_date', 'between', [doc.from_date, doc.to_date]], ['roster_type','=',"Basic"]], fields=['name'])
                    if shift_assignemnt:
                        update_shift_assignment(shift_assignemnt[0].name, doc )
                if shift_worker == 1:
                    # check for existing schedule
                    schedule_date_range = [str(i.date()) for i in pd.date_range(start=doc.from_date, end=doc.to_date)]
                    found_schedules_date = []
                    existing_schedules = frappe.db.sql(f""" SELECT name, date FROM `tabEmployee Schedule`
                        WHERE employee="{doc.employee}" AND roster_type="{doc.roster_type}"
                        AND date BETWEEN '{doc.from_date}' AND '{doc.to_date}' """, as_dict=1)
                    if existing_schedules:
                        # update existing schedule
                        for es in existing_schedules:
                            start_time, end_time = frappe.db.get_value("Shift Type", doc.shift_type, ['start_time', 'end_time'])
                            end_date = es.date
                            if start_time > end_time:
                                end_date = add_days(end_date, 1)

                            frappe.db.set_value('Employee Schedule', es.name, {
                                'shift':doc.operations_shift,
                                'shift_type':doc.shift_type,
                                'start_datetime': f"{es.date} {start_time}",
                                'end_datetime': f"{end_date} {end_time}",
                                'operations_role':doc.operations_role,
                                'post_abbrv': role_abbr,
                                'employee_availability':'Working',
                                'roster_type':doc.roster_type,
                                'department':doc.department,
                                'site':doc.site,
                                'reference_doctype': doc.doctype,
                                'reference_docname': doc.name,
                            })
                            found_schedules_date.append(str(es.date))
                    # create new schedule
                    new_date_range = [i for i in schedule_date_range if not i in found_schedules_date]
                    if new_date_range:
                        for date in new_date_range:
                            if frappe.db.exists("Employee Schedule", {'date':date, 'employee':doc.employee, 'employee_availability':'Day Off'}):
                                es = frappe.get_doc("Employee Schedule", {'date':date, 'employee':doc.employee, 'employee_availability':'Day Off'})
                                start_time, end_time = frappe.db.get_value("Shift Type", doc.shift_type, ['start_time', 'end_time'])
                                end_date = es.date
                                if start_time > end_time:
                                    end_date = add_days(end_date, 1)


                                frappe.db.set_value('Employee Schedule', es.name, {
                                    'shift':doc.operations_shift,
                                    'shift_type':doc.shift_type,
                                    'start_datetime': f"{es.date} {start_time}",
                                    'end_datetime': f"{end_date} {end_time}",
                                    'operations_role':doc.operations_role,
                                    'post_abbrv': role_abbr,
                                    'employee_availability':'Working',
                                    'roster_type':doc.roster_type,
                                    'department':doc.department,
                                    'site':doc.site,
                                    'reference_doctype': doc.doctype,
                                    'reference_docname': doc.name
                                    }
                                )
                            else:
                                create_employee_schedule_from_request(doc, d)

def update_shift_assignment(shift_assignemnt,shift_request):
    assignment_doc = frappe.get_doc('Shift Assignment', shift_assignemnt)
    project = frappe.db.get_value("Operations Shift", {'name':shift_request.operations_shift}, ['project'])
    assignment_doc.db_set("company" , shift_request.company)
    assignment_doc.db_set("shift" , shift_request.operations_shift)
    assignment_doc.db_set("roster_type" , shift_request.roster_type)
    assignment_doc.db_set("shift_type" , shift_request.shift_type)
    assignment_doc.db_set("site" , shift_request.site)
    assignment_doc.db_set("project" , project)
    assignment_doc.db_set("site_location" , shift_request.check_in_site)
    assignment_doc.db_set("employee" , shift_request.employee)
    assignment_doc.db_set("start_date" , shift_request.from_date)
    assignment_doc.db_set("shift_request" , shift_request.name)
    assignment_doc.db_set("check_in_site" , shift_request.check_in_site)
    assignment_doc.db_set("check_out_site" , shift_request.check_out_site)
    shift_type_data = frappe.get_doc("Shift Type",shift_request.shift_type)
    if shift_type_data:
        start_datetime = datetime.datetime.strptime(f"{shift_request.from_date} {(datetime.datetime.min + shift_type_data.start_time).time()}", '%Y-%m-%d %H:%M:%S')
        if shift_type_data.end_time.total_seconds() < shift_type_data.start_time.total_seconds():
            end_datetime = datetime.datetime.strptime(f"{add_days(assignment_doc.start_date, 1)} {(datetime.datetime.min + shift_type_data.end_time).time()}", '%Y-%m-%d %H:%M:%S')
        else:
            end_datetime = datetime.datetime.strptime(f"{assignment_doc.start_date} {(datetime.datetime.min + shift_type_data.end_time).time()}", '%Y-%m-%d %H:%M:%S')

        assignment_doc.db_set("start_datetime" ,start_datetime)
        assignment_doc.db_set("end_datetime" , end_datetime)
    if shift_request.operations_role:
        assignment_doc.db_set("operations_role" , shift_request.operations_role)

def replace_shift_assignment(shift_assignemnt, shift_request):
    '''
        Method used to create Shift Assignment from Shift Request
        args:
            shift_request: Object of shift request
            submit: Boolean
    '''
    #Replace Existing Assignment
    assignment_doc = frappe.get_doc('Shift Assignment', shift_assignemnt)
    project = frappe.db.get_value("Operations Shift", {'name':shift_request.operations_shift}, ['project'])
    assignment_doc.db_set("company" , shift_request.company)
    assignment_doc.db_set("shift" , shift_request.operations_shift)
    assignment_doc.db_set("roster_type" , shift_request.roster_type)
    assignment_doc.db_set("shift_type" , shift_request.shift_type)
    assignment_doc.db_set("site" , shift_request.site)
    assignment_doc.db_set("project" , project)
    assignment_doc.db_set("site_location" , shift_request.check_in_site)
    assignment_doc.db_set("employee" , shift_request.employee)
    assignment_doc.db_set("start_date" , shift_request.from_date)
    assignment_doc.db_set("shift_request" , shift_request.name)
    assignment_doc.db_set("check_in_site" , shift_request.check_in_site)
    assignment_doc.db_set("check_out_site" , shift_request.check_out_site)
    assignment_doc.db_set("employee_is_replaced",1)
    shift_type_data = frappe.get_doc("Shift Type",shift_request.shift_type)
    if shift_type_data:
        start_datetime = datetime.datetime.strptime(f"{shift_request.from_date} {(datetime.datetime.min + shift_type_data.start_time).time()}", '%Y-%m-%d %H:%M:%S')
        if shift_type_data.end_time.total_seconds() < shift_type_data.start_time.total_seconds():
            end_datetime = datetime.datetime.strptime(f"{add_days(assignment_doc.start_date, 1)} {(datetime.datetime.min + shift_type_data.end_time).time()}", '%Y-%m-%d %H:%M:%S')
        else:
            end_datetime = datetime.datetime.strptime(f"{assignment_doc.start_date} {(datetime.datetime.min + shift_type_data.end_time).time()}", '%Y-%m-%d %H:%M:%S')

        assignment_doc.db_set("start_datetime" ,start_datetime)
        assignment_doc.db_set("end_datetime" , end_datetime)
    if shift_request.operations_role:
        assignment_doc.db_set("operations_role" , shift_request.operations_role)
    employee_checkin_update = frappe.db.sql(f"""UPDATE `tabEmployee Checkin` SET employee_is_replaced=1 WHERE shift_assignment='{shift_assignemnt}'""")

def replace_employee_schedule(doc, existing_schedules, schedule_date_range):
    try:
        # replace existing schedule
        for es in existing_schedules:
            start_time, end_time = frappe.db.get_value("Shift Type", doc.shift_type, ['start_time', 'end_time'])
            end_date = es.date
            if start_time > end_time:
                end_date = add_days(end_date, 1)

            frappe.db.set_value('Employee Schedule', es.name, {
                'shift':doc.operations_shift,
                'shift_type':doc.shift_type,
                'start_datetime': f"{es.date} {start_time}",
                'end_datetime': f"{end_date} {end_time}",
                'operations_role':doc.operations_role,
                'post_abbrv': role_abbr,
                'employee_availability':'Working',
                'roster_type':doc.roster_type,
                'department':doc.department,
                'site':doc.site,
                'reference_doctype': doc.doctype,
                'reference_docname': doc.name,
                'employee_is_replaced':1
            })
    except Exception as e:
        frappe.throw(_("Error Replacing Employee Schedule"))
        frappe.log_error(frappe.get_traceback(), "Error Replacing Employee Schedule")

def create_shift_assignment_from_request(shift_request, submit=True):
    '''
        Method used to create Shift Assignment from Shift Request
        args:
            shift_request: Object of shift request
            submit: Boolean
    '''
    assignment_doc = frappe.new_doc("Shift Assignment")
    assignment_doc.company = shift_request.company
    assignment_doc.shift = shift_request.operations_shift
    assignment_doc.roster_type = shift_request.roster_type
    assignment_doc.shift_type = shift_request.shift_type
    assignment_doc.employee = shift_request.employee
    assignment_doc.start_date = shift_request.from_date
    assignment_doc.shift_request = shift_request.name
    assignment_doc.check_in_site = shift_request.check_in_site
    assignment_doc.check_out_site = shift_request.check_out_site
    if shift_request.operations_role:
        assignment_doc.operations_role = shift_request.operations_role
    assignment_doc.insert()
    if submit:
        assignment_doc.submit()
    frappe.db.commit()

def create_employee_schedule_from_request(doc, date):
    schedule = frappe.new_doc("Employee Schedule")
    schedule.employee = doc.employee
    schedule.date = date
    schedule.shift = doc.operations_shift
    schedule.shift_type = doc.shift_type
    schedule.operations_role = doc.operations_role
    schedule.post_abbrv = role_abbr
    schedule.employee_availability = 'Working'
    schedule.roster_type = doc.roster_type
    schedule.department = doc.department
    schedule.site = doc.site
    schedule.reference_doctype = doc.doctype
    schedule.reference_docname = doc.name
    schedule.save(ignore_permissions=True)

def assign_day_off(shift_request):
    shift_assignment = frappe.get_list('Shift Assignment' ,{'employee':shift_request.employee, 'start_date': shift_request.from_date}, ['name'])
    if shift_assignment:
        for s in shift_assignment:
            del_employee_checkin = frappe.db.sql(f"""DELETE from `tabEmployee Checkin` WHERE employee='{shift_request.employee}' AND shift_assignment='{s.name}'""")
            shift = frappe.get_doc("Shift Assignment", s.name)
            if shift.start_date >= getdate():
                frappe.db.sql(f"""DELETE from `tabShift Assignment` WHERE name='{shift.name}'""")

    employee_schedule = frappe.get_list('Employee Schedule' ,{'employee':shift_request.employee, 'date': ["between",  (shift_request.from_date, shift_request.to_date)]}, ['name'])
    if employee_schedule:
        for es in employee_schedule:
            schedule = frappe.get_doc("Employee Schedule", es.name)
            schedule.employee_availability = 'Day Off'
            schedule.save()
    else:
        start_date = datetime.datetime.strptime(shift_request.from_date, '%Y-%m-%d')
        end_date = datetime.datetime.strptime(shift_request.to_date, '%Y-%m-%d')
        delta = datetime.timedelta(days=1)
        while start_date <= end_date:
            schedule = frappe.new_doc("Employee Schedule")
            schedule.employee = shift_request.employee
            schedule.date = start_date
            schedule.employee_availability = 'Day Off'
            schedule.save()
            start_date += delta
    frappe.db.commit()

def cancel_shift_assignment_of_request(shift_request):
    '''
        Method used to cancel Shift Assignment of a Shift Request
        args:
            shift_request: Object of shift request
            submit: Boolean
    '''
    schedule_exists = frappe.db.exists("Employee Schedule",{"employee":shift_request.employee, "date":cstr(getdate()), "employee_availability":"Working"})

    shift_assignment_list = frappe.get_list(
        "Shift Assignment",
        {
            "employee": shift_request.employee,
            "shift_request": shift_request.name,
            "docstatus": 1
        }
    )
    if shift_assignment_list:
        for shift in shift_assignment_list:
            shift_assignment_doc = frappe.get_doc("Shift Assignment", shift["name"])
            shift_assignment_doc.cancel()
            shift_assignment_doc.delete()
    if shift_request.from_date <= cstr(getdate()) <= shift_request.to_date and schedule_exists:
        schedule = frappe.get_doc("Employee Schedule",{"employee":shift_request.employee, "date":cstr(getdate())})
        if schedule:
            sa = frappe.get_doc(dict(
            doctype='Shift Assignment',
            start_date = cstr(getdate()),
            employee = schedule.employee,
            employee_name = schedule.employee_name,
            department = schedule.department,
            operations_role = schedule.operations_role,
            shift = schedule.shift,
            site = schedule.site,
            project = schedule.project,
            shift_type = schedule.shift_type,
            roster_type = schedule.roster_type,
            )).insert()
            sa.submit()


def validate_approver(self):
    shift, department = frappe.get_value("Employee", self.employee, ["shift","department"])

    approvers = frappe.db.sql(
        """select approver from `tabDepartment Approver` where parent= %s and parentfield = 'shift_request_approver'""",
        (department),
    )

    approvers = [approver[0] for approver in approvers]

    if frappe.db.exists("Employee", self.employee,["reports_to"]):
        report_to = frappe.get_value("Employee", self.employee,["reports_to"])
        approvers.append(frappe.get_value("Employee", report_to, "user_id"))


    if shift:
            shift_supervisor = frappe.get_value("Operations Shift", shift, "supervisor")
            approvers.append(frappe.get_value("Employee", shift_supervisor, "user_id"))

    if self.approver not in approvers:
        frappe.throw(_("Only Approvers can Approve this Request."))

@frappe.whitelist()
def fetch_approver(employee):
    project_list = frappe.db.get_all("Project List", {'parent':'Operation Settings'}, ['project'], pluck='project')
    if employee:
        employee_detail = frappe.get_all("Employee", {"employee":employee}, ["*"])
        reports_to = employee_detail[0].reports_to
        department = employee_detail[0].department
        project_alloc = employee_detail[0].project
        shift_worker = employee_detail[0].shift_working
        if shift_worker == 0:
            if reports_to:
                return frappe.get_value("Employee", reports_to, "user_id")
        else:
            if project_alloc not in project_list and department == "Operations - ONEFM":
                approvers = frappe.db.sql(
                    """select approver from `tabDepartment Approver` where parent= %s and parentfield = 'shift_request_approver'""",
                    (department),
                )
                approvers = [approver[0] for approver in approvers]
                return approvers[0]
            else:
                project_manager = frappe.get_value("Project", project_alloc, ["account_manager"])
                if reports_to:
                    return frappe.get_value("Employee", reports_to, "user_id")
                elif project_manager:
                    return frappe.get_value("Employee", project_manager, "user_id")

def fill_to_date(doc, method):
    if not doc.to_date:
        doc.to_date = doc.from_date

def validate_from_date(doc, method):
    if doc.purpose != 'Assign Day Off' and not (frappe.session.user == get_employee_user_id(frappe.db.get_single_value("ONEFM General Setting","attendance_manager"))):
        if getdate(today()) > getdate(doc.from_date):
            frappe.throw(
                _("Please note that Shift Requests cannot be created for a past date."),
                title=_("Invalid Start Date"),
		    )

@frappe.whitelist()
def update_request(shift_request, from_date, to_date):
    from_date = getdate(from_date)
    to_date = getdate(to_date)
    if getdate(today()) > from_date:
        frappe.throw(
                _("Please note that Shift Requests cannot be updated to a past date."),
                title=_("Invalid Start Date"),
		    )
    if from_date > to_date:
        frappe.throw('To Date cannot be before From Date.')
    shift_request_obj = frappe.get_doc('Shift Request', shift_request)
    shift_request_obj.db_set("from_date", from_date)
    shift_request_obj.db_set("to_date", to_date)
    shift_request_obj.db_set("update_request", True)
    shift_request_obj.db_set("status", 'Draft')
    apply_workflow(shift_request_obj, "Update Request")

def _get_employee_from_user(user):
	employee_docname = frappe.db.get_value("Employee", {"user_id": user})
	return employee_docname if employee_docname else None


def get_manager(doctype,employee):
    """Return the instances of the doctype where the employee is the supervisor

    Args:
        doctype : Valid Doctype
        employee (_type_): Valid Employee ID

    Returns:
        _type_: _description_
    """
    field = None
    if doctype =="Project":
        field = 'account_manager'
    elif doctype =='Operations Site':
        field = 'account_supervisor'
    elif doctype =='Operations Shift':
        field = 'supervisor'
    if field:
        values = frappe.get_all(doctype,{field:employee},['name'])
        if values:
            return [i.name for i in values]



@frappe.whitelist()
def fetch_employee_details(employee):
    emp_data = frappe.get_all("Employee",{'name':employee},['employee_name','company','shift','site','project','default_shift','department'])
    return emp_data[0] if emp_data else []

@frappe.whitelist()
def get_employees(doctype, txt, searchfield, start, page_len, filters):
    """
    Return the full list of employees if current user has a HR role or Included in the Employee Master Table.
    else, it returns the full list of employees assigned to the Operations shifts,sites or projects where this user is set

    """

    is_master= False
    default_user_roles = None
    employee_master_roles = frappe.get_all("ONEFM Document Access Roles Detail",{'parent':"ONEFM General Setting",'parentfield':"employee_master_role"},['role'])
    user_roles = frappe.get_roles(frappe.session.user) or []
    default_user_roles = [i.role for i in employee_master_roles] if employee_master_roles else  ['HR Manager',"HR User"]
    #if user has any default hr role
    if [role for role in user_roles if role in default_user_roles ]:
            is_master = True
    if  is_master:
        #If the user has not typed anything on the employee field
        if not txt:
            employees = frappe.db.sql("Select name,employee_name,employee_id from `tabEmployee` where status = 'Active' ")
            return employees
        else:
            #If the user has  typed anything on the employee field
            employees = frappe.db.sql(f"Select name,employee_name,employee_id from `tabEmployee` where status = 'Active' and name like '%{txt}%' or employee_name like '%{txt}%' or employee_id like '%{txt}%'   ")
            return employees

    else:
        allowed_employees = []
        user = frappe.session.user
        if user!="Administrator":
            employee_id = _get_employee_from_user(user)
            if employee_id:
                employee_base_query = f"""
                        SELECT name,employee_name,employee_id from `tabEmployee` where status = "Active"
                """
                cond_str = ""
                query = None
                allowed_employees.append(employee_id)
                #get all reports to
                reports_to = frappe.get_all("Employee",{'reports_to':employee_id,'status':"Active"},'name')
                if reports_to:
                    allowed_employees+=[i.name for i in reports_to]
                #get all employees in  project,shift and site
                if allowed_employees:
                    cond_str = f" and name in  {tuple(allowed_employees)}" if len(allowed_employees)>1 else f" and name = '{allowed_employees[0]}'"
                    if txt:
                        cond_str+=f" and (name like '%{txt}%' or employee_name like '%{txt}%' or employee_id like '%{txt}%')  "
                    query=employee_base_query+cond_str
                shifts = get_manager('Operations Shift',employee_id)
                if shifts:
                    cond_str = f" and shift in {tuple(shifts)}" if len(shifts)>1 else f" and shift = '{shifts[0]}'"
                    if txt:
                        cond_str+=f" and (name like '%{txt}%' or employee_name like '%{txt}%' or employee_id like '%{txt}%')  "
                    query += f""" UNION SELECT name,employee_name,employee_id from `tabEmployee` where status = "Active"  {cond_str} """
                sites = get_manager('Operations Site',employee_id)
                if sites:
                    cond_str = f" and site in {tuple(sites)}" if len(sites)>1 else f" and site = '{sites[0]}'"
                    if txt:
                        cond_str+=f" and (name like '%{txt}%' or employee_name like '%{txt}%' or employee_id like '%{txt}%')  "
                    query += f""" UNION SELECT name,employee_name,employee_id from `tabEmployee` where status = "Active"  {cond_str} """
                project = get_manager('Project',employee_id)
                if project:
                    cond_str = f" and project in {tuple(project)}" if len(project)>1 else f" and project = '{project[0]}'"
                    if txt:
                        cond_str+=f" and (name like '%{txt}%' or employee_name like '%{txt}%' or employee_id like '%{txt}%')  "
                    query += f""" UNION SELECT name,employee_name,employee_id from `tabEmployee` where status = "Active"  {cond_str} """
                #Check if employee is set in operations shift, operations site or project

                return frappe.db.sql(query)


            else:
                return ()
        else:
            if not txt:
                return frappe.db.sql("Select name,employee_name,employee_id from `tabEmployee` where status = 'Active' ")
            else:
                return frappe.db.sql("Select name,employee_name,employee_id from `tabEmployee` where status = 'Active' and name \
                    like '%{txt}%' or employee_name like '%{txt}%' \or employee_id like '%{txt}%'  ")

def check_for_roster(doc):
    schedule_date_range = [str(i.date()) for i in pd.date_range(start=doc.from_date, end=doc.to_date)]
    new_date_range = [i for i in schedule_date_range]
    if new_date_range:
        for date in new_date_range:
            if frappe.db.exists("Employee Schedule", {'date':date, 'employee':doc.employee}):
                return True
            elif frappe.db.exists("Shift Assignment", {'start_date':date, 'employee':doc.employee}):
                return True
            else:
                return False

@frappe.whitelist()
def get_operations_role(doctype, txt, searchfield, start, page_len, filters):
    shift = filters.get('operations_shift')
    operations_roles = frappe.db.sql("""
        SELECT DISTINCT name
        FROM `tabOperations Role`
        WHERE shift="{shift}"
    """.format(shift=shift))
    return operations_roles

def has_overlap(shift1, shift2):
    shift1 = frappe.get_doc("Shift Type", shift1)
    shift2 = frappe.get_doc("Shift Type", shift2)
    if shift1.end_time <= shift2.start_time or shift1.start_time >= shift2.end_time:
        return True #No Overlap
    else:
        return False #Overlap

def daterange(start_date, end_date):
    start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
    for n in range(int((end_date - start_date).days)):
        yield start_date + datetime.timedelta(n)
