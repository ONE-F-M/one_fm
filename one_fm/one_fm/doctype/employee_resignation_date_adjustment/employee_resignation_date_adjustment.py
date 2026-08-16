import frappe
from frappe.model.document import Document
from frappe import _

class EmployeeResignationDateAdjustment(Document):
    def validate(self):
        self.set_approver()
        self.validate_extended_relieving_date()

    def validate_extended_relieving_date(self):
        # mandatory_depends_on on the field only enforces this in the browser --
        # it's never checked server-side, so a Draft can be saved without it,
        # but "Submit for Review" and beyond must not proceed without it.
        if self.workflow_state and self.workflow_state != "Draft" and not self.extended_relieving_date:
            frappe.throw(
                _("Extended Relieving Date is mandatory before submitting this request for review."),
                title=_("Missing Extended Relieving Date"),
            )

    def on_update(self):
        self.clear_manual_assignments()
        self.process_extension_approval()
        self.notify_offboarding_on_submission()
        
    def notify_offboarding_on_submission(self):
        if self.workflow_state == "Pending Supervisor":
            old_doc = self.get_doc_before_save()
            if not old_doc or old_doc.workflow_state != "Pending Supervisor":
                subject = _("Attention: Resignation Extension Initiated - {0}").format(self.name)
                message = _("A resignation extension request <b>{0}</b> has been submitted to the supervisor. Please hold any offboarding processing for the involved employees until this is finalized.").format(self.name)
                
                recipients = set()
                from frappe.utils.user import get_users_with_role
                offboarding_officers = get_users_with_role("Offboarding Officer")
                for user in offboarding_officers:
                    recipients.add(user)
                    
                if recipients:
                    from one_fm.processor import sendemail
                    sendemail(
                        recipients=list(recipients),
                        subject=subject,
                        message=message,
                        reference_doctype=self.doctype,
                        reference_name=self.name
                    )

    def clear_manual_assignments(self):
        if not self.is_new():
            old_doc = self.get_doc_before_save()
            if old_doc and old_doc.workflow_state == "Pending Supervisor" and self.workflow_state != "Pending Supervisor":
                from frappe.desk.form.assign_to import remove
                if getattr(self, "supervisor", None):
                    try:
                        remove(self.doctype, self.name, self.supervisor)
                    except Exception:
                        pass
        
    def process_extension_approval(self):
        if not self.is_new():
            old_doc = self.get_doc_before_save()
            if (
                old_doc
                and old_doc.workflow_state != "Approved"
                and self.workflow_state == "Approved"
            ):
                if not self.extended_relieving_date:
                    frappe.throw(
                        _("Extended Relieving Date is mandatory."),
                        title=_("Missing Extended Relieving Date")
                    )
                    
                # 1. Update Employee Resignation parent Doc
                if self.employee_resignation:
                    resignation = frappe.get_doc("Employee Resignation", self.employee_resignation)
                    resignation.db_set("relieving_date", self.extended_relieving_date)

                    # 2. Update the Employee linked to the parent resignation
                    if self.employee:
                        frappe.db.set_value("Employee", self.employee, "relieving_date", self.extended_relieving_date)

                    # 3. Update Project Manpower Request Deployment Date securely
                    pmr_name = frappe.db.get_value("Project Manpower Request", {"employee_resignation": self.employee_resignation}, "name")
                    if pmr_name:
                        pmr = frappe.get_doc("Project Manpower Request", pmr_name)
                        from frappe.utils import add_days
                        ojt = pmr.ojt_days or 0
                        revised_deployment_date = add_days(self.extended_relieving_date, -ojt)
                        pmr.db_set("deployment_date", revised_deployment_date)

                        # Step 4: Notify the Recruiter
                        if getattr(pmr, "recruiter", None):
                            from one_fm.processor import sendemail
                            sendemail(
                                recipients=[pmr.recruiter],
                                subject=_("Action Required: Deployment Date Adjusted for PR {0}").format(pmr.name),
                                message=_("An employee involved in PR <b>{0}</b> has had their resignation date adjusted. The new deployment date for the replacement has been automatically updated to <b>{1}</b>. Please adjust your hiring schedules accordingly.").format(pmr.name, revised_deployment_date),
                                reference_doctype="Project Manpower Request",
                                reference_name=pmr.name
                            )

    def set_approver(self):
        if not self.employee and self.employee_resignation:
            self.employee = frappe.db.get_value("Employee Resignation", self.employee_resignation, "employee")

        if not self.employee:
            return

        employee_details = frappe.db.get_value(
            "Employee", self.employee, ["reports_to", "site", "project"], as_dict=True
        )

        if not employee_details:
            return

        approver_employee = None

        if employee_details.reports_to:
            approver_employee = employee_details.reports_to
        if not approver_employee and employee_details.site:
            approver_employee = frappe.db.get_value("Operations Site", employee_details.site, "site_supervisor")
        if not approver_employee and employee_details.project:
            approver_employee = frappe.db.get_value("Project", employee_details.project, "project_manager")

        if approver_employee:
            approver_user = frappe.db.get_value("Employee", approver_employee, "user_id")
            if approver_user and frappe.db.exists("User", approver_user):
                self.supervisor = approver_user
            else:
                self.supervisor = None

        # Reuse the exact same routing/actors already resolved on the originating
        # Employee Resignation -- fetch rather than re-derive.
        if self.employee_resignation:
            resignation = frappe.db.get_value(
                "Employee Resignation", self.employee_resignation,
                ["shift_working", "shift_category", "t4_route", "t4_admin",
                 "cleaning_head_supervisor", "security_manager", "project_manager"],
                as_dict=True,
            )
            if resignation:
                self.is_corporate = 0 if resignation.shift_working else 1
                self.shift_category = resignation.shift_category
                self.t4_route = resignation.t4_route
                self.t4_admin = resignation.t4_admin
                self.cleaning_head_supervisor = resignation.cleaning_head_supervisor
                self.security_manager = resignation.security_manager
                self.project_manager = resignation.project_manager

        # Set Offboarding Officer — first user with that role
        if not self.get("offboarding_officer"):
            from frappe.utils.user import get_users_with_role
            om_users = get_users_with_role("Offboarding Officer")
            if om_users:
                self.offboarding_officer = om_users[0]

