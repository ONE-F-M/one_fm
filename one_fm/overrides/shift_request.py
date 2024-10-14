import frappe
import datetime, json
import pandas as pd
from frappe import _
from frappe.utils import getdate, today, cstr, add_to_date, add_days, get_url_to_form
from frappe.model.workflow import apply_workflow
from frappe.utils import getdate, cstr
from hrms.hr.utils import share_doc_with_approver
from hrms.hr.doctype.shift_request.shift_request import *
from one_fm.utils import (
    workflow_approve_reject, send_workflow_action_email, get_approver
)
from one_fm.api.notification import get_employee_user_id
from one_fm.operations.doctype.operations_shift.operations_shift import get_supervisor_operations_shifts
from one_fm.processor import sendemail


class OverlappingShiftError(frappe.ValidationError):
    pass

class ShiftRequestOverride(ShiftRequest):
    def validate(self):
        # ensure status is not pending
        if self.is_new():
            self.status='Draft'
        if self.status=='Pending Approval':
            self.status == 'Draft'

        process_shift_assignemnt(self) # set shift assignment and employee schedule

    def on_submit(self):
        if self.workflow_state != 'Update Request':
            self.db_set("status", self.workflow_state) if self.workflow_state!='Pending Approval' else self.db_set("status", 'Draft')

    def before_save(self):
        # Fill 'To' date if not set
        if not self.to_date:
            self.to_date = self.from_date

        # Validate 'From' date
        if not self.assign_day_off:
            if getdate(today()) > getdate(self.from_date):
                frappe.throw('From Date cannot be before today.')
        
        send_shift_request_mail(self)

    def on_update(self):
        for approver in self.custom_shift_approvers:
            share_doc_with_approver(self, approver.user)

        if self.workflow_state in ['Approved', 'Rejected']:
            workflow_approve_reject(self, [get_employee_user_id(self.employee)])

        if self.workflow_state == 'Draft':
            send_workflow_action_email(self,[approver.user for approver in self.custom_shift_approvers])
            validate_shift_overlap(self)

    def validate_approver(self):
        if not self.is_new() and self.workflow_state == "Approved":
            pass
            # if self.approver != frappe.session.user:
            # frappe.throw(_("Only Approvers can Approve this Request."))

    def on_cancel(self):
        '''
            Method used to override Shift Request on_cancel
        '''
        self.cancel_shift_assignment_of_request()

    def validate_default_shift(self):
        default_shift = frappe.get_value("Employee", self.employee, "default_shift")
        if self.shift_type == default_shift:
            pass


    def cancel_shift_assignment_of_request(self):
        '''
            Method used to cancel Shift Assignment of a Shift Request
            args:
                self: Object of shift request
                submit: Boolean
        '''
        schedule_exists = frappe.db.exists("Employee Schedule",{"employee":self.employee, "date":cstr(getdate()), "employee_availability":"Working"})

        shift_assignment_list = frappe.get_list(
            "Shift Assignment",
            {
                "employee": self.employee,
                "shift_request": self.name,
                "docstatus": 1
            }
        )
        if shift_assignment_list:
            for shift in shift_assignment_list:
                shift_assignment_doc = frappe.get_doc("Shift Assignment", shift["name"])
                shift_assignment_doc.cancel()
                shift_assignment_doc.delete()
        if self.from_date <= cstr(getdate()) <= self.to_date and schedule_exists:
            schedule = frappe.get_doc("Employee Schedule",{"employee":self.employee, "date":cstr(getdate())})
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


def on_update_after_submit(doc, method):
    if doc.update_request:
        if doc.workflow_state == 'Update Request':
            doc.db_set("status", 'Draft')
            doc.cancel_shift_assignment_of_request()

def process_shift_assignemnt(doc, event=None):
    role_abbr = frappe.db.get_value("Operations Role",doc.operations_role,'post_abbrv')
    if doc.workflow_state=='Approved' and doc.docstatus==1:
        if doc.assign_day_off == 1:
            assign_day_off(doc)
        else:
            if doc.roster_type == "Basic" and cstr(doc.from_date) == cstr(getdate()):
                shift_assignemnt = frappe.get_value("Shift Assignment", {'employee':doc.employee, 'start_date': doc.from_date, 'roster_type':"Basic"}, ['name'])
                if shift_assignemnt:
                    update_shift_assignment(shift_assignemnt, doc )
                else:
                    create_shift_assignment_from_request(doc)

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

                    # validate_operations_post_overfill({es.date: 1}, doc.operations_shift)

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
                    })
                    found_schedules_date.append(str(es.date))
            # create new schedule
            new_date_range = [i for i in schedule_date_range if not i in found_schedules_date]
            if new_date_range:
                for d in new_date_range:
                    if frappe.db.exists("Employee Schedule", {'date':d, 'employee':doc.employee, 'employee_availability':'Day Off'}):
                        es = frappe.get_doc("Employee Schedule", {'date':d, 'employee':doc.employee, 'employee_availability':'Day Off'})
                        start_time, end_time = frappe.db.get_value("Shift Type", doc.shift_type, ['start_time', 'end_time'])
                        end_date = es.date
                        if start_time > end_time:
                            end_date = add_days(end_date, 1)

                        # validate_operations_post_overfill({es.date: 1}, doc.operations_shift)

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
                        schedule = frappe.new_doc("Employee Schedule")
                        schedule.employee = doc.employee
                        schedule.date = d
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

def assign_day_off(shift_request):
    shift_assignment = frappe.get_list('Shift Assignment' ,{'employee':shift_request.employee, 'start_date': shift_request.from_date}, ['name'])
    if shift_assignment:
        for s in shift_assignment:
            shift = frappe.get_doc("Shift Assignment", s.name)
            if shift.start_date >= getdate():
                shift.cancel()
                shift.delete()

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


@frappe.whitelist()
def fetch_approver(doc):
    doc = frappe._dict(json.loads(doc))
    employee_user_id = get_employee_user_id(doc.employee)
    approver = get_approver(doc.employee)
    approver_user_id = get_employee_user_id(approver)
    other_approvers = []
    if doc.department == "Operations - ONEFM":
        other_approvers =[user.approver for user in frappe.get_all("Department Approver", filters={"parent": doc.department, "parentfield": "shift_request_approver"}, fields=["approver"]) if user.approver != employee_user_id and user.approver != approver_user_id]

    if approver_user_id:
        return [approver_user_id] + other_approvers

@frappe.whitelist()
def update_request(shift_request, from_date, to_date):
    from_date = getdate(from_date)
    to_date = getdate(to_date)
    if getdate(today()) > from_date:
        frappe.throw('From Date cannot be before today.')
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


def get_manager(doctype, employee):
    """Return the instances of the doctype where the employee is the supervisor

    Args:
        doctype : Valid Doctype
        employee (_type_): Valid Employee ID

    Returns:
        _type_: _description_
    """
    if doctype =="Operations Shift":
        return get_supervisor_operations_shifts(employee)

    else:
        field_map = {"Project": "account_manager", "Operations Site": "account_supervisor"}
        if doctype in field_map:
            values = frappe.get_all(doctype, {field_map[doctype]:employee},['name'])
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


def send_shift_request_mail(doc):
    if doc.workflow_state == 'Pending Approval':
        try:
            title = f"Urgent Notification: {doc.doctype} Requires Your Immediate Review"
            context = dict(
                employee_name=doc.employee_name,
                from_date=doc.from_date,
                to_date=doc.to_date,
                department=doc.department,
                checkin_site=doc.check_in_site,
                checkout_site=doc.check_out_site,
                doc_link=get_url_to_form(doc.doctype, doc.name)
            )
            msg = frappe.render_template('one_fm/templates/emails/shift_request_notification.html', context=context)
            recipients = [approver.user for approver in doc.custom_shift_approvers]
            sendemail(recipients=recipients, subject=title, content=msg)
        except:
            frappe.log_error(frappe.get_traceback(), "Error while sending shift request notification")
