import frappe
from frappe import _
from frappe.utils import get_fullname
from hrms.hr.doctype.leave_application.leave_application import *
from one_fm.processor import sendemail
from frappe.desk.form.assign_to import add


class LeaveApplicationOverride(LeaveApplication):
    def after_insert(self):
        self.assign_to_leave_approver()
        
    def validate(self):
        validate_active_employee(self.employee)
        set_employee_name(self)
        self.validate_dates()
        
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

        if (
                self.half_day
                and self.half_day_date
                and (
                getdate(self.half_day_date) < getdate(self.from_date)
                or getdate(self.half_day_date) > getdate(self.to_date)
        )
        ):

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