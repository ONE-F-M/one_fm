import frappe, json
import datetime
from frappe import _
import pandas as pd
from frappe.workflow.doctype.workflow_action.workflow_action import (
    get_common_email_args, deduplicate_actions, get_next_possible_transitions,
    get_doc_workflow_state, get_workflow_name, get_users_next_action_data
)
from frappe.utils import getdate, today, cstr, add_to_date, nowdate
from frappe.model.workflow import apply_workflow
from one_fm.utils import (workflow_approve_reject, send_workflow_action_email)
from one_fm.api.notification import create_notification_log, get_employee_user_id

class OverlappingShiftError(frappe.ValidationError):
    pass

def validate(doc, event=None):
    # ensure status is not pending
    if doc.is_new():
        doc.status='Draft'
    if doc.status=='Pending Approval':
        doc.status == 'Draft'

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
                    frappe.db.set_value('Employee Schedule', es.name, {
                        'shift':doc.operations_shift,
                        'shift_type':doc.shift_type,
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
                        frappe.db.set_value('Employee Schedule', es.name, {
                            'shift':doc.operations_shift,
                            'shift_type':doc.shift_type,
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
            shift = schedule.operations_shift,
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