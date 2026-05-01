import frappe
from frappe.model.document import Document
from frappe import _

class EmployeeResignationExtension(Document):
    def validate(self):
        self.set_approver()

    def on_update(self):
        self.clear_manual_assignments()
        self.process_extension_approval()
        self.notify_offboarding_on_submission()
        
    def notify_offboarding_on_submission(self):
        # Notify Offboarding Officer when state hits 'Pending Supervisor'
        if self.workflow_state == "Pending Supervisor":
            old_doc = self.get_doc_before_save()
            if not old_doc or old_doc.workflow_state != "Pending Supervisor":
                recipients = set()
                from frappe.utils.user import get_users_with_role
                from one_fm.api.v1.utils import resolve_active_user
                offboarding_officers = get_users_with_role("Offboarding Officer")
                for user in offboarding_officers:
                    recipients.add(resolve_active_user(user))
                
                if recipients:
                    subject = _("Attention: Resignation Extension Initiated - {0}").format(self.name)
                    message = _("A resignation extension request <b>{0}</b> has been submitted to the supervisor. Please hold any offboarding processing for the involved employees until this is finalized.").format(self.name)
                    
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
            # Only remove the manually attached supervisor when moving out of the Supervisor state
            if old_doc and old_doc.workflow_state == "Pending Supervisor" and self.workflow_state != "Pending Supervisor":
                if self.supervisor:
                    from frappe.desk.form.assign_to import remove
                    try:
                        remove(self.doctype, self.name, self.supervisor, ignore_permissions=True)
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
                    from frappe import _
                    frappe.throw(
                        _("Extended Relieving Date is mandatory."),
                        title=_("Missing Extended Relieving Date")
                    )
                    
                # 1. Update Employee Resignation parent Doc
                if self.employee_resignation:
                    resignation = frappe.get_doc("Employee Resignation", self.employee_resignation)
                    resignation.db_set("relieving_date", self.extended_relieving_date)
                    
                    # 2. Update all Employees natively linked to the parent resignation batch!
                    if self.get("employees"):
                        for row in self.employees:
                            if row.employee:
                                frappe.db.set_value("Employee", row.employee, "relieving_date", self.extended_relieving_date)

                    # 3. Update Project Manpower Request Deployment Date securely
                    pmr_name = frappe.db.get_value("Project Manpower Request", {"employee_resignation": self.employee_resignation}, "name")
                    if pmr_name:
                        pmr = frappe.get_doc("Project Manpower Request", pmr_name)
                        from frappe.utils import add_days
                        ojt = pmr.ojt_days or 0
                        revised_deployment_date = add_days(self.extended_relieving_date, -ojt)
                        pmr.db_set("deployment_date", revised_deployment_date)


    def set_approver(self):
        if not self.get("employees"):
            return
            
        first_employee = self.employees[0].employee
        if not first_employee:
            return

        employee_details = frappe.db.get_value(
            "Employee", first_employee, ["reports_to", "site", "project"], as_dict=True
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
                if frappe.db.has_column("Employee Resignation Extension", "supervisor"):
                    self.supervisor = approver_user
            else:
                if frappe.db.has_column("Employee Resignation Extension", "supervisor"):
                    self.supervisor = None

        # Set Operations Manager from the resignation document
        if self.employee_resignation:
            rsgn_om = frappe.db.get_value("Employee Resignation", self.employee_resignation, "operations_manager")
            if rsgn_om and frappe.db.has_column("Employee Resignation Extension", "operations_manager"):
                self.operations_manager = rsgn_om

        # Set Offboarding Officer — first user with that role
        if not self.get("offboarding_officer") and frappe.db.has_column("Employee Resignation Extension", "offboarding_officer"):
            from frappe.utils.user import get_users_with_role
            om_users = get_users_with_role("Offboarding Officer")
            if om_users:
                self.offboarding_officer = om_users[0]

