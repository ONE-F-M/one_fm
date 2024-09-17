from ast import literal_eval
import frappe,json

from frappe import _
from frappe.utils import get_fullname, nowdate, add_to_date
from hrms.hr.doctype.leave_application.leave_application import *
from one_fm.processor import sendemail
from frappe.desk.form.assign_to import add,remove
from erpnext.crm.utils import get_open_todos
from one_fm.api.notification import create_notification_log
from frappe.utils import getdate, date_diff
import pandas as pd
from one_fm.api.api import push_notification_rest_api_for_leave_application
from one_fm.processor import is_user_id_company_prefred_email_in_employee
from hrms.hr.utils import get_holidays_for_employee
from one_fm.api.tasks import get_action_user,remove_assignment

from .employee import NotifyAttendanceManagerOnStatusChange



def validate_active_staff(doc,event):
    emp_details = frappe.get_value("Employee",doc.employee,['status','relieving_date'],as_dict =1 )
    if emp_details.status != "Active" and emp_details.relieving_date:
        if getdate(emp_details.relieving_date)<getdate(doc.to_date):
            frappe.throw("The Employee Specified in the leave application is not Active.\nAlso, the leave application date exceeds the employee relieving date")


def close_leaves(leave_ids, user=None):
    approved_leaves = leave_ids
    not_approved_leaves = []
    for leave in leave_ids:
        try:
            leave_doc = frappe.get_doc("Leave Application", leave)
            leave_doc.status = "Approved"
            leave_doc.flags.ignore_validate = True
            leave_doc.submit()
        except:
            frappe.log_error("Error while closing {0}".format(leave))
            approved_leaves.remove(leave)
            not_approved_leaves.append(leave)
            continue
    frappe.db.commit()
    if user:
        message = "Please note that,"
        if approved_leaves and len(approved_leaves)>0:
            message += "<br/>the approved leave(s) are {0}".format(approved_leaves)
        if not_approved_leaves and len(not_approved_leaves)>0:
            message += "<br/>not approved leave(s) are {0}".format(not_approved_leaves)
        doc = frappe.new_doc('Notification Log')
        doc.subject = 'Close selected leave application'
        doc.email_content = message
        doc.for_user = user
        doc.save(ignore_permissions=True)

@frappe.whitelist()
def fix_sick_leave(names):
    selected_leaves = json.loads(names)
    if selected_leaves:
        if len(selected_leaves) <= 5:
            close_leaves(selected_leaves, frappe.session.user)
        else:
            frappe.enqueue(method=close_leaves, user=frappe.session.user, leave_ids=selected_leaves, queue='long',timeout=1200,job_name='Closing Leaves')
    else:
        frappe.throw("Please select atleast 1 row")

def is_app_user(emp):
    #Returns true if an employee is an app user or has a valid email address
    try:
        is_app_user = False
        user_details = frappe.get_all("Employee",{'name':emp},['user_id','employee_id'])
        if user_details:
            user_id = user_details[0].get("user_id")
            emp_id = user_details[0].get("employee_id")
            if user_id.split("@")[0].lower() == emp_id.lower():
                is_app_user = True
        return is_app_user
    except:
        pass


class LeaveApplicationOverride(LeaveApplication):
    def onload(self):
        leave_attendances = frappe.db.get_all("Attendance", {"leave_application": self.name}, "name")
        attendance_not_created = False
        if self.total_leave_days > len(leave_attendances):
            attendance_not_created = True
        self.set_onload("attendance_not_created", attendance_not_created)

    def validate(self):
        self.validate_applicable_after()

    def close_todo(self):
        """Close the Todo document linked with a leave application
        """
        try:
            leave_todo = frappe.get_all("ToDo",{'reference_name':self.name},['name'])
            if leave_todo:
                for each in leave_todo:
                    frappe.db.set_value("ToDo",each.get("name"),'status','Closed')
                frappe.db.commit()
        except:
            frappe.log_error(frappe.get_traceback(),"Error Closing ToDos")

    def on_submit(self):
        self.close_todo()
        self.close_shifts()
        return super().on_submit()
        self.db_set('status', 'Approved')

    def validate_applicable_after(self):
        if self.leave_type:
            leave_type = frappe.get_doc("Leave Type", self.leave_type)
            if leave_type.applicable_after > 0:
                date_of_joining = frappe.db.get_value("Employee", self.employee, "date_of_joining")
                leave_days = get_approved_leaves_for_period(
                    self.employee, False, date_of_joining, self.from_date
                )
                number_of_days = date_diff(getdate(self.from_date), date_of_joining)
                if number_of_days >= 0:
                    number_of_days = number_of_days - leave_days
                    if number_of_days < leave_type.applicable_after:
                        frappe.throw(
                            _("{0} applicable after {1} working days").format(
                                self.leave_type, leave_type.applicable_after
                            )
                        )
                        
    def validate_reliever(self):
        if self.custom_reliever_ == self.employee:
            frappe.throw("Oops! You can't assign yourself as the reliever!")

    def close_shifts(self):
        #delete the shifts if a leave application is approved
        try:
            if self.status == "Approved":
                shift_assignment = frappe.db.sql(f"""SELECT name from `tabShift Assignment` where employee = '{self.employee}' and start_date BETWEEN '{self.from_date}' and '{self.to_date}' and docstatus = 1 """, as_dict=True)
                for shift in shift_assignment:
                    #unlink from attendance check
                    self.unlink_attendance_check(shift.name)
                    query =f"""DELETE from `tabShift Assignment` where name = '{shift.name}' and docstatus = 1 """
                    frappe.db.sql(query)
                frappe.msgprint(msg = f"Shift Assignments for {self.employee_name} between {self.from_date} and {self.to_date} have been deleted",alert=1)
        except:
            frappe.log_error(frappe.get_traceback(),"Error Closing Shifts")

    def unlink_attendance_check(self, shift):
        attcheck_exists = frappe.db.exists("Attendance Check",  {"shift_assignment": shift})
        if attcheck_exists:
            frappe.db.set_value("Attendance Check", attcheck_exists, {'shift_assignment': "",'has_shift_assignment': 0})
        frappe.db.commit()

    def custom_notify_employee(self):
        template = frappe.db.get_single_value("HR Settings", "leave_status_notification_template")
        if not template:
            frappe.msgprint(_("Please set default template for Leave Status Notification in HR Settings."))
            return
        parent_doc = frappe.get_doc("Leave Application", self.name)
        args = parent_doc.as_dict()
        email_template = frappe.get_doc("Email Template", template)
        message = frappe.render_template(email_template.response, args)
        if is_app_user(self.employee):
            push_notification_rest_api_for_leave_application(self.employee,email_template.subject,message,self.name)
            frappe.msgprint(_("Push notification sent to {0} via mobile application").format(self.employee),alert=True)
        else:
            employee = frappe.get_doc("Employee", self.employee)
            if not employee.user_id:
                return
            sendemail(recipients= [employee.user_id], subject="Leave Application", message=message,
                    reference_doctype=self.doctype, reference_name=self.name, attachments = [])
            frappe.msgprint("Email Sent to Employee {}".format(employee.employee_name))
            
            
    def notify_employee(self):
        self.enqueue_notification_method(self.custom_notify_employee)

    def validate(self):
        validate_active_employee(self.employee)
        set_employee_name(self)
        self.validate_reliever()
        self.validate_dates()
        self.update_attachment_name()
        self.validate_balance_leaves()
        self.validate_leave_overlap()
        self.validate_max_days()
        self.show_block_day_warning()
        self.validate_block_days()
        self.validate_salary_processed_days()
        self.validate_attendance()
        self.set_half_day_date()
        if frappe.db.get_value("Leave Type", self.leave_type, "is_optional_leave"):
            self.validate_optional_leave()
        self.validate_applicable_after()

    @frappe.whitelist()
    def update_attendance(self):
        if self.status != "Approved":
            return
        if self.total_leave_days > 20:
            frappe.enqueue(update_attendance_recods, self=self, is_async=True)
        else:
            update_attendance_recods(self)

    def create_or_update_attendance(self, attendance_name, date, status):
        if attendance_name:
            # update existing attendance, change absent to on leave
            doc = frappe.get_doc("Attendance", attendance_name)
            if doc.status != status and status == 'On Leave':
                doc.db_set({"status": status, "leave_type": self.leave_type, "leave_application": self.name})
            if doc.status != status and status == 'Holiday':
                doc.db_set({"status": status})
        else:
            # make new attendance and submit it
            doc = frappe.new_doc("Attendance")
            doc.employee = self.employee
            doc.employee_name = self.employee_name
            doc.attendance_date = date
            doc.company = self.company
            if status == "On Leave":
                doc.leave_type = self.leave_type
                doc.leave_application = self.name
            doc.status = status
            doc.flags.ignore_validate = True
            doc.insert(ignore_permissions=True)
            doc.save()
            doc.submit()

    @frappe.whitelist()
    def notify_leave_approver(self):
        """
        This function is to notify the leave approver and request his action.
        The Message sent through mail consist of 2 action: Approve and Reject.(It is sent only when the not sick leave.)

        Param: doc -> Leave Application Doc (which needs approval)

        It's a action that takes place on update of Leave Application.
        """
        #If Leave Approver Exist
        
        if self.leave_approver:
            try:
                args = dict(self.as_dict()) #fetch fields from the doc.
                args.update({"base_url": frappe.utils.get_url()})

                #Fetch Email Template for Leave Approval. The email template is in HTML format.
                template = frappe.db.get_single_value('HR Settings', 'leave_approval_notification_template')
                if not template:
                    frappe.msgprint(_("Please set default template for Leave Approval Notification in HR Settings."))
                    return
                email_template = frappe.get_doc("Email Template", template)
                message = frappe.render_template(email_template.response_html, args)

                if self.proof_documents:
                    proof_doc = self.proof_documents
                    for p in proof_doc:
                        message+=f"<hr><img src='{p.attachments}' height='400'/>"

                #send notification
                sendemail(recipients= [self.leave_approver], subject="Leave Application", message=message,
                        reference_doctype=self.doctype, reference_name=self.name, attachments = [])

                employee_id = frappe.get_value("Employee", {"user_id":self.leave_approver}, ["name"])

                if self.total_leave_days == 1:
                    date = "for "+cstr(self.from_date)
                else:
                    date = "from "+cstr(self.from_date)+" to "+cstr(self.to_date)

                push_notication_message = self.employee_name+" has applied for "+self.leave_type+" "+date+". Kindly, take action."
                push_notification_rest_api_for_leave_application(employee_id,"Leave Application", push_notication_message, self.name)
            except Exception as e:
                frappe.log_error(message=frappe.get_traceback(), title="Leave Notification")

    def after_insert(self):
        self.assign_to_leave_approver()
        self.update_attachment_name()
        self.enqueue_notification_method(self.notify_leave_approver)
        
    def enqueue_notification_method(self,method):
        frappe.enqueue(method,is_async=True, job_name= str("Leave Notification"),  queue="short")
        
    def update_attachment_name(self):
        if self.proof_documents:
            for each in self.proof_documents:
                if each.attachments:
                    all_files = frappe.get_all("File",{'file_url':each.attachments},['attached_to_name','name'])
                    if all_files and 'new' in all_files[0].attached_to_name:
                        frappe.db.set_value("File",all_files[0].name,'attached_to_name',self.name)

    def validate_attendance(self):
        pass

    def assign_to_leave_approver(self):
        #This function is meant to create a TODO for the leave approver
                try:
                    if self.name and self.leave_type =="Sick Leave":
                        existing_assignment = frappe.get_all("ToDo",{'allocated_to':self.leave_approver,'reference_name':self.name})
                        if not existing_assignment:
                            frappe.get_doc(
                                {
                                    "doctype": "ToDo",
                                    "allocated_to": self.leave_approver,
                                    "reference_type": "Leave Application",
                                    "reference_name": self.name,
                                    "description": f'Please note that leave application {self.name} is awaiting your approval',
                                    "priority": "Medium",
                                    "status": "Open",
                                    "date": nowdate(),
                                    "assigned_by": frappe.session.user,
                                }
                            ).insert(ignore_permissions=True)
                except:
                    frappe.log_error(frappe.get_traceback(),"Error assigning to User")
                    frappe.throw("Error while assigning leave application")

    def validate_dates(self):
        if frappe.db.get_single_value("HR Settings", "restrict_backdated_leave_application"):
            if self.from_date and getdate(self.from_date) < getdate(self.posting_date):
                allowed_role = frappe.db.get_single_value(
                    "HR Settings", "role_allowed_to_create_backdated_leave_application"
                )
                user = frappe.get_doc("User", frappe.session.user)
                user_roles = [d.role for d in user.roles]
                if not allowed_role:
                    frappe.throw(
                        _("Backdated Leave Application is restricted. Please set the {} in {}").format(
                            frappe.bold("Role Allowed to Create Backdated Leave Application"),
                            get_link_to_form("HR Settings", "HR Settings"),
                        )
                    )

                if allowed_role and allowed_role not in user_roles:
                    frappe.throw(
                        _("Only users with the {0} role can create backdated leave applications").format(
                            allowed_role
                        )
                    )

        if self.from_date and self.to_date and (getdate(self.to_date) < getdate(self.from_date)):
            frappe.throw(_("To date cannot be before from date"))

        if self.half_day and self.half_day_date:
            half_day_date = getdate(self.half_day_date)
            if half_day_date < getdate(self.from_date) or half_day_date > getdate(self.to_date):
                frappe.throw(_("Half Day Date should be between From Date and To Date"))

        if not is_lwp(self.leave_type):
            self.validate_dates_across_allocation()
            self.validate_back_dated_application()

    @frappe.whitelist()
    def notify(self, args):
        args = frappe._dict(args)
        # args -> message, message_to, subject
        if cint(self.follow_via_email):
            contact = args.message_to
            if not isinstance(contact, list):
                if not args.notify == "employee":
                    contact = frappe.get_doc("User", contact).email or contact

            sender = dict()
            sender["email"] = frappe.get_doc("User", frappe.session.user).email
            sender["full_name"] = get_fullname(sender["email"])
            # if is_user_id_company_prefred_email_in_employee(contact):
            try:
                sendemail(
                    recipients=[contact],
                    sender=sender["email"],
                    subject=args.subject,
                    message=args.message,
                )

                frappe.msgprint(_("Email sent to {0}").format(contact))
            except frappe.OutgoingEmailError:
                pass
            except:
                frappe.log_error(frappe.get_traceback(),"Error Sending Notification")

    def on_cancel(self):
        if self.status == "Cancelled"  and self.leave_type == 'Annual Leave' and getdate(self.from_date) <= getdate() <= getdate(self.to_date):
            emp = frappe.get_doc("Employee", self.employee)
            emp.status = "Active"
            emp.save()
            frappe.db.commit()
        self.create_leave_ledger_entry(submit=False)
        # notify leave applier about cancellation
        self.cancel_attendance()


    def validate_attendance_check(self):
        """
            Validate if there are any draft attendance checks for the period and update
        """
        try:
            if frappe.db.exists("Attendance Check",{'docstatus':0,'employee':self.employee, 'date': ['between', (getdate(self.from_date), getdate(self.to_date))]}):
                att_checks = frappe.get_all("Attendance Check",{'docstatus':0,'employee':self.employee, 'date': ['between', (getdate(self.from_date), getdate(self.to_date))]},['name'])
                if att_checks:
                    for each in att_checks:
                        frappe.db.set_value("Attendance Check",each.name,'workflow_state','Approved')
                        frappe.db.set_value("Attendance Check",each.name,'attendance_status','On Leave')
                        frappe.db.set_value("Attendance Check",each.name,'docstatus',1)
                        remove_assignment(each.name)
            frappe.db.commit()
        except:
            frappe.log_error(title = "Error Updating Attendance Check",message=frappe.get_traceback())
            frappe.throw("An Error Occured while updating Attendance Checks. Please review the error logs")

    def on_update(self):
        if self.status=='Rejected':
            self.notify_employee()
            attendance_range = []
            for i in pd.date_range(self.from_date, self.to_date):
                attendance_range.append(getdate(i))
            for i in attendance_range:
                if getdate()>i:
                    if frappe.db.exists("Attendance", {
                        'employee':self.employee,
                        'attendance_date': str(i),
                        'docstatus':1
                        }):
                        frappe.db.sql(f"""
                            UPDATE `tabAttendance` SET status='Absent', comment="Leave Appication {self.name} Rejected"
                            WHERE attendance_date='{str(i)}' and employee='{self.employee}'
                        """)
                    else:
                        frappe.get_doc({
                            'doctype':'Attendance',
                            'employee':self.employee,
                            'attendance_date':str(i),
                            'roster_type':'Basic',
                            'status':'Absent'
                        }).submit()

                    frappe.db.commit()
        if self.status == "Approved":
            if getdate(self.from_date) <= getdate() <= getdate(self.to_date):
                # frappe.db.set_value(), will not call the validate.
                if self.leave_type !='Sick Leave':
                    frappe.db.set_value("Employee", self.employee, "status", "Vacation")
            self.validate_attendance_check()
        self.clear_employee_schedules()


    def clear_employee_schedules(self):
        last_doc = self.get_doc_before_save()
        if last_doc and last_doc.get('workflow_state') != self.workflow_state:
            if self.workflow_state == "Approved":
                frappe.db.sql(
                    '''
                    DELETE FROM `tabEmployee Schedule` WHERE
                    employee = %s AND
                    date BETWEEN %s AND %s;
                    ''', (self.employee, self.from_date, self.to_date)
                )


def update_attendance_recods(self):
    if self.status != "Approved":
        return

    holiday_dates = []
    if self.leave_type == 'Annual Leave' :
        holidays = get_holidays_for_employee(employee=self.employee, start_date=self.from_date, end_date=self.to_date, only_non_weekly=True)
        holiday_dates = [cstr(h.holiday_date) for h in holidays]

    for dt in daterange(getdate(self.from_date), getdate(self.to_date)):
        date = dt.strftime("%Y-%m-%d")
        attendance_name = frappe.db.exists(
            "Attendance", dict(employee=self.employee, attendance_date=date, docstatus=("!=", 2))
        )

        # don't mark attendance for holidays
        # if leave type does not include holidays within leaves as leaves
        if date in holiday_dates:
            if attendance_name:
                # cancel and delete existing attendance for holidays
                attendance = frappe.get_doc("Attendance", attendance_name)
                attendance.flags.ignore_permissions = True
                if attendance.docstatus == 1:
                    attendance.db_set('status','Holiday')
                    frappe.db.commit()
            else:
                self.create_or_update_attendance(attendance_name, date, 'Holiday')
        else:
            self.create_or_update_attendance(attendance_name, date, 'On Leave')

    frappe.msgprint(_("Attendance are created for the leave Appication {0}!".format(self.name)), alert=True)


def remove_assignment(attendance_check):
    open_todo = get_open_todos("Attendance Check",attendance_check)
    if open_todo:
        for each in open_todo:
            remove("Attendance Check",attendance_check,each.allocated_to,ignore_permissions=1)
    

@frappe.whitelist()
def get_leave_details(employee, date):
    allocation_records = get_leave_allocation_records(employee, date)
    leave_allocation = {}
    precision = cint(frappe.db.get_single_value("System Settings", "float_precision", cache=True))

    for d in allocation_records:
        allocation = allocation_records.get(d, frappe._dict())
        remaining_leaves = get_leave_balance_on(
            employee, d, date, to_date=allocation.to_date, consider_all_leaves_in_the_allocation_period=True
        )

        end_date = allocation.to_date
        leaves_taken = get_leaves_for_period(employee, d, allocation.from_date, end_date) * -1
        leaves_pending = get_leaves_pending_approval_for_period(
            employee, d, allocation.from_date, end_date
        )
        expired_leaves = allocation.total_leaves_allocated - (remaining_leaves + leaves_taken)

        leave_allocation[d] = {
            "total_leaves": flt(allocation.total_leaves_allocated, precision),
            "expired_leaves": flt(expired_leaves, precision) if expired_leaves > 0 else 0,
            "leaves_taken": flt(leaves_taken, precision),
            "leaves_pending_approval": flt(leaves_pending, precision),
            "remaining_leaves": flt(remaining_leaves, precision),
        }

    # is used in set query
    lwp = frappe.get_list("Leave Type", filters={"is_lwp": 1}, pluck="name")

    return {
        "leave_allocation": leave_allocation,
        "leave_approver": get_leave_approver(employee),
        "lwps": lwp,
    }

@frappe.whitelist()
def get_leave_approver(employee):
    employee_details = frappe.db.get_value(
			"Employee",
			{"name": employee},
			["reports_to", "department"],
			as_dict = True
		)
    reports_to = employee_details.get('reports_to')
    department = employee_details.get('department')
    employee_shift = frappe.get_list("Shift Assignment",fields=["*"],filters={"employee":employee}, order_by='creation desc',limit_page_length=1)
    approver = False
    if reports_to:
        approver = frappe.get_value("Employee", reports_to, ["user_id"])
    elif len(employee_shift) > 0 and employee_shift[0].shift:
        approver, Role = get_action_user(employee,employee_shift[0].shift)
    else:
        approvers = frappe.db.sql(
                """select approver from `tabDepartment Approver` where parent= %s and parentfield = 'leave_approvers'""",
                (department),
            )
        if approvers and len(approvers) > 0:
            approvers = [approver[0] for approver in approvers]
            approver = approvers[0]
    return approver

@frappe.whitelist()
def employee_leave_status():
    """
    This method is to change the status of employee Doc from Active to Vacation, when Leave starts.
    It also changes it back to Active when the leave ends.
    The method is called as a cron job before  assigning shift.
    """
    today = getdate()
    yesterday = add_to_date(today, days=-1)


    start_leave = frappe.get_list("Leave Application", {'from_date': today, 'status':'Approved'}, ['employee', "name", "custom_reliever_"])
    end_leave = frappe.get_list("Leave Application", {'to_date': yesterday, 'status':'Approved'}, ['employee', 'name'])


    frappe.enqueue(process_change,start_leave=start_leave,end_leave=end_leave, is_async=True, queue="long")



def process_change(start_leave, end_leave):
    change_employee_status(start_leave, "Vacation")
    change_employee_status(end_leave, "Active")

def change_employee_status(employee_list, status):
    for e in employee_list:
        frappe.db.set_value("Employee", e.employee, "status", status)
        try:
            if status == "Vacation" and e.custom_reliever_:
                reassign_to_reliever(reliever=e.custom_reliever_, leave_name=e.name, employee=e.employee)

            if status == "Active" :
                reassign_to_applicant(employee=e.employee, leave_name=e.name)
        except:
            frappe.log_error(frappe.get_traceback(), "Error occurred while trying to reassign duties")
        
    frappe.db.commit()


def reassign_to_reliever(reliever: str, leave_name: str, employee: str):
    try:
        reliever_employee = frappe.db.get_value("Employee", reliever, ["name", "user_id"], as_dict=1)
        employee = frappe.db.get_value("Employee", employee, ["name", "user_id"], as_dict=1)
        reassign = ReassignDutiesToReliever(reliever=reliever_employee, leave_name=leave_name, employee_object=employee)
        reassign.reassign()
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Reassign Employee Duties To Reliever")


def reassign_to_applicant(employee: str, leave_name: str):
    try:
        reassigned_documents = frappe.db.get_list("Reassigned Documents", filters={"parent": leave_name}, fields=["reassigned_doctype", "names"])
        if reassigned_documents:
            employee = frappe.db.get_value("Employee", employee, ["name", "user_id"], as_dict=1)
            reassign = ReassignDocumentToLeaveApplicant(reassigned_documents=reassigned_documents, employee=employee)
            reassign.reassign()
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Reassign Duties Back To Employee")


class ReassignDutiesToReliever(NotifyAttendanceManagerOnStatusChange):


    def __init__(self, reliever: dict, leave_name: str, employee_object: dict) -> None:
        super().__init__(employee_object)
        self._reliever = reliever
        self._reassigned_documents = dict()
        self._leave_name = leave_name
    
    def reassign_operations_shift_supervisor(self):
        operation_shift_supervisors = self._operations_shift_supervisor
        if operation_shift_supervisors:
            for obj in operation_shift_supervisors:
                frappe.db.set_value("Operations Shift", obj, "supervisor", self._reliever.name)
            self._reassigned_documents.update({"Operations Shift": operation_shift_supervisors})


    def reassign_operations_site_supervisor(self):
        operations_site_supervisor = self._operations_site_supervisor
        if operations_site_supervisor:
            for obj in operations_site_supervisor:
                frappe.db.set_value("Operations Site", obj, "account_supervisor", self._reliever.name)
            self._reassigned_documents.update({"Operations Site": operations_site_supervisor})


    def reassign_projects_manager(self):
        projects_manager = self._projects_manager
        if projects_manager:
            for obj in projects_manager:
                frappe.db.set_value("Project", obj, "account_manager", self._reliever.name)
            self._reassigned_documents.update({"Project": projects_manager})
    
    def reassign_reports_to(self):
        reports_to = self._employee_reports_to
        if reports_to:
            for obj in reports_to:
                frappe.db.set_value("Employee", obj, "reports_to", self._reliever.name)
            self._reassigned_documents.update({"Employee": [obj.name for obj in reports_to]})


    def reassign_operations_manager(self):
        if self._operation_manager:
            frappe.db.set_value("Operation Settings", "Operation Settings", "default_operation_manager", self._reliever.user_id)
            self._reassigned_documents.update({"Operation Settings": ["default_operation_manager", ]})

    def reassign_attendance_manager(self):
        if self._attendance_manager:
            frappe.db.set_value("ONEFM General Setting", "ONEFM General Setting", "attendance_manager", self._reliever.name)
            self._reassigned_documents.update({"ONEFM General Setting": ["attendance_manager",]})


    def reassign(self):
        self.reassign_operations_shift_supervisor()
        self.reassign_operations_site_supervisor()
        self.reassign_projects_manager()
        self.reassign_reports_to()
        self.reassign_operations_manager()
        self.reassign_attendance_manager()
        if self._reassigned_documents:
            for key, value in self._reassigned_documents.items():
                reassigned_documents = frappe.new_doc('Reassigned Documents')
                reassigned_documents.parent=self._leave_name,
                reassigned_documents.parentfield="custom_reassigned_documents"
                reassigned_documents.parenttype="Leave Application"
                reassigned_documents.reassigned_doctype=key
                reassigned_documents.names=str(value)
                reassigned_documents.insert()
                

class ReassignDocumentToLeaveApplicant:

    def __init__(self, reassigned_documents: list, employee: dict):
        self._employee = employee
        self._reassigned_documents = reassigned_documents

    
    def reassign_operations_site(self, sites: list):
        for obj in sites:
            frappe.db.set_value("Operations Site", obj, "account_supervisor", self._employee.name)

    
    def reassign_operation_shift(self, shifts: list):
        for obj in shifts:
            frappe.db.set_value("Operations Shift", obj, "supervisor", self._employee.name)

    def reassign_projects(self, projects: list):
        for obj in projects:
            frappe.db.set_value("Project", obj, "account_manager", self._employee.name)

    def reassign_reports_to(self, reports_to: list):
        for obj in reports_to:
            frappe.db.set_value("Employee", obj, "reports_to", self._employee.name)
            
    def reassign_general_settings(self, settings: list):
        for obj in settings:
            frappe.db.set_value("Operation Settings", "Operation Settings", obj, self._employee.user_id)
            
    def reassign_operation_settings(self, settings: list):
        for obj in settings:
            frappe.db.set_value("ONEFM General Setting", "ONEFM General Setting", obj, self._employee.name)
            
    
    def reassign(self):
        documents = {obj.get("reassigned_doctype"): literal_eval(obj.get("names"))for obj in self._reassigned_documents}
        for key, value in documents.items():
            if key == "Operations Site":
                self.reassign_operations_site(sites=value)
            
            if key == "Operations Shift":
                self.reassign_operation_shift(shifts=value)

            if key == "Project":
                self.reassign_projects(projects=value)

            if key == "Employee":
                self.reassign_reports_to(reports_to=value)
            
            if key == "Operation Settings":
                self.reassign_general_settings(settings=value)
            
            if key == "ONEFM General Setting":
                self.reassign_operation_settings(settings=value)


            

