import frappe
from frappe import _
from frappe.utils import get_fullname
from hrms.hr.doctype.leave_application.leave_application import *
from one_fm.processor import sendemail
from frappe.desk.form.assign_to import add
from one_fm.api.notification import create_notification_log
from frappe.utils import getdate
import pandas as pd
from one_fm.api.api import push_notification_rest_api_for_leave_application
from one_fm.processor import is_user_id_company_prefred_email_in_employee

def close_leaves(all_leaves,user=None):
    for each in all_leaves:
        try:
            leave_doc = frappe.get_doc("Leave Application",each.name)
            leave_doc.status = "Approved"
            leave_doc.flags.ignore_validate = True
            leave_doc.submit()
        except:
            frappe.log_error("Error while closing {}".format(each.name))
            continue
    frappe.db.commit()
    if user:
        message = "Please note that all open sick leaves have been approved"
        create_notification_log('Leaves Closed!', 'Please note that all sick leaves in draft have closed.', [user],leave_doc)


@frappe.whitelist()
def fix_sick_leave():
    all_leaves = frappe.get_all("Leave Application",{'leave_type':"Sick Leave","docstatus":0})
    if all_leaves:
        if len(all_leaves)<=5:
            close_leaves(all_leaves)
        else:
            frappe.enqueue(method=close_leaves,user=frappe.session.user,all_leaves = all_leaves, queue='long',timeout=1200,job_name='Closing Leaves')
            frappe.msgprint("Leaves are being closed in the background, <br> You will recieve a notification after the process.",alert = 1)


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
    
        

    def notify_employee(self):
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
            self.notify(
                {
                    # for post in messages
                    "message": message,
                    "message_to": employee.user_id,
                    # for email
                    "subject": email_template.subject,
                    "notify": "employee",
                }
            )

    def validate(self):
        validate_active_employee(self.employee)
        set_employee_name(self)
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



    def update_attachment_name(self):
        if self.proof_documents:
            for each in self.proof_documents:
                if each.attachments:
                    all_files = frappe.get_all("File",{'file_url':each.attachments},['attached_to_name','name'])
                    if all_files and 'new' in all_files[0].attached_to_name:
                        frappe.db.set_value("File",all_files[0].name,'attached_to_name',self.name)
        
    def after_insert(self):
        self.assign_to_leave_approver()
        self.update_attachment_name()
        

    def validate_attendance(self):
        pass

    def assign_to_leave_approver(self):
        #This function is meant to create a TODO for the leave approver
                try:
                    if self.name and self.leave_type =="Sick Leave":
                        existing_assignment = frappe.get_all("ToDo",{'allocated_to':self.leave_approver,'reference_name':self.name})
                        if not existing_assignment:
                            args = {
                                'assign_to':[self.leave_approver],
                                'doctype':"Leave Application",
                                'name':self.name,
                                'description':f'Please note that leave application {self.name} is awaiting your approval',
                            }
                            add(args)
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
            if is_user_id_company_prefred_email_in_employee(contact):
                try:
                    sendemail(
                        recipients=contact,
                        sender=sender["email"],
                        subject=args.subject,
                        message=args.message,
                    )
                    frappe.msgprint(_("Email sent to {0}").format(contact))
                except frappe.OutgoingEmailError:
                    pass

    def on_update(self):
        if self.workflow_state=='Rejected':
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

@frappe.whitelist()
def get_leave_approver(employee):
    leave_approver, department = frappe.db.get_value(
        "Employee", employee, ["leave_approver", "department"]
    )

    if not leave_approver and department:
        leave_approver = frappe.db.get_value(
            "Department Approver",
            {"parent": department, "parentfield": "leave_approvers", "idx": 1},
            "approver",
        )

    return leave_approver
