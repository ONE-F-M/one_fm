# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class EmployeeResignationWithdrawal(Document):
	def on_update(self):
		self.clear_manual_assignments()
		self.validate_rejection_reason()
		self.process_withdrawal_approval()
		self.notify_offboarding_on_submission()

	def clear_manual_assignments(self):
		if not self.is_new():
			old_doc = self.get_doc_before_save()
			# Only remove the manually explicitly mapped supervisor Assignment
			if old_doc and old_doc.workflow_state == "Pending Supervisor" and self.workflow_state != "Pending Supervisor":
				if self.supervisor:
					from frappe.desk.form.assign_to import remove
					try:
						remove(self.doctype, self.name, self.supervisor, ignore_permissions=True)
					except Exception:
						pass

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
					subject = _("Attention: Resignation Withdrawal Initiated - {0}").format(self.name)
					message = _("A resignation withdrawal request <b>{0}</b> has been submitted to the supervisor. Please hold any offboarding processing for the involved employees.").format(self.name)
					
					from one_fm.processor import sendemail
					sendemail(
						recipients=list(recipients),
						subject=subject,
						message=message,
						reference_doctype=self.doctype,
						reference_name=self.name
					)

	def process_withdrawal_approval(self):
		if not self.is_new():
			old_doc = self.get_doc_before_save()
			if (
				old_doc
				and old_doc.workflow_state != "Approved"
				and self.workflow_state == "Approved"
			):
				approved_count = 0
				
				# Step 1: Process every remaining explicitly grouped candidate in the grid (only those who actually had a reason/attachment provided)
				if self.get("employees"):
					for row in self.employees:
						if row.reason and row.attachment:
							approved_count += 1
							
							# A. Fully reset Employee resignation fields — withdrawal reverses the resignation
							if row.employee:
								frappe.db.set_value("Employee", row.employee, {
									"relieving_date": None,
									"resignation_date": None,
									"resignation_letter_date": None,
									"resignation_status": None,
									"current_resignation": None
								}, update_modified=False)
								
							# B. Mark the original Resignation row as Approved
							if self.employee_resignation:
								item_name = frappe.db.get_value("Employee Resignation Item", {"parent": self.employee_resignation, "employee": row.employee}, "name")
								if item_name:
									frappe.db.set_value("Employee Resignation Item", item_name, "withdrawal_status", "Approved")

				# Step 2: Handle PMR counters mathematically and gracefully sync status
				if self.employee_resignation and approved_count > 0:
					resignation = frappe.get_doc("Employee Resignation", self.employee_resignation)
					total_in_batch = len(resignation.get("employees", []))
					
					total_withdrawn_count = frappe.db.count("Employee Resignation Item", filters={"parent": self.employee_resignation, "withdrawal_status": "Approved"})
					
					pmr_name = frappe.db.get_value("Project Manpower Request", {"employee_resignation": self.employee_resignation}, "name")
					if pmr_name:
						pmr = frappe.get_doc("Project Manpower Request", pmr_name)
						if pmr.docstatus < 2:
							# Increase PMR withdrawal tracking natively in the child table matrix!
							withdrawal_row_found = False
							for f_row in pmr.get("fulfillment_actions", []):
							    if f_row.action_type == "Resignation Withdrawal":
							        f_row.qty = (f_row.qty or 0) + approved_count
							        withdrawal_row_found = True
							        break
							        
							if not withdrawal_row_found:
							    pmr.append("fulfillment_actions", {
							        "action_type": "Resignation Withdrawal",
							        "qty": approved_count
							    })
							
							# Recalculate remaining quantities automatically
							if hasattr(pmr, 'calculate_remaining_qty'):
								pmr.calculate_remaining_qty()

								pmr.save(ignore_permissions=True)
								
								# Auto-close/set status if entirely withdrawn
								if (pmr.remaining_qty or 0) == 0:
									withdrawal_qty = sum((row.qty or 0) for row in pmr.get("fulfillment_actions", []) if row.action_type == "Resignation Withdrawal")
									if withdrawal_qty >= (pmr.count or 0):
										pmr.db_set("workflow_state", "Withdrawn")
							
							# Step 3: Simply notify the recruiter that a withdrawal occurred.
							# We do NOT cancel the PMR here; the Recruiter will handle closure manually.
							if getattr(pmr, "recruiter", None):
								from one_fm.processor import sendemail
								sendemail(
									recipients=[pmr.recruiter],
									subject=_("Action Required: Withdrawal on PR {0}").format(pmr.name),
									message=_("An employee involved in PR <b>{0}</b> has withdrawn their resignation. Please review the 'Fulfillment Actions' table and close the request if no longer needed.").format(pmr.name),
									reference_doctype="Project Manpower Request",
									reference_name=pmr.name
								)
					
					# Step 4: Flag Parent Resignation if entirely withdrawn
					if total_withdrawn_count >= total_in_batch:
						# All employees withdrawn, mark parent workflow state as Resignation Withdrawn
						if frappe.db.has_column("Employee Resignation", "workflow_state"):
							resignation.db_set("workflow_state", "Withdrawn")

	def validate(self):
		self.set_approver()
		if self.employee_resignation:
			pmr_name = frappe.db.get_value("Project Manpower Request", {"employee_resignation": self.employee_resignation}, "name")
			if pmr_name:
				pmr_wf_state = frappe.db.get_value("Project Manpower Request", pmr_name, "workflow_state")
				
				if pmr_wf_state in ["Completed", "Closed", "Fulfilled", "Hired"]:
					frappe.throw(_("Cannot withdraw resignation because the replacement Project Manpower Request ({0}) has already been completed or fulfilled. A replacement has likely already been hired. Please contact HR.").format(pmr_name))


	def validate_rejection_reason(self):
		if not self.is_new():
			old_doc = self.get_doc_before_save()
			if (
				old_doc
				and old_doc.workflow_state in ["Pending Supervisor", "Accepted by Supervisor","Rejected By Supervisor"]
				and self.workflow_state in ["Rejected By Supervisor","Rejected"]
			):
				if not getattr(self, "reason_for_rejection", None):
					frappe.throw(_("Please provide Reason for Rejection"))

	def set_approver(self):
		if not self.get("employees"):
			return
			
		# Derive supervisor from the FIRST employee listed (same logic as resignation)
		first_employee = self.employees[0].employee
		if not first_employee:
			return

		employee_details = frappe.db.get_value(
			"Employee", first_employee, ["reports_to", "site", "project"], as_dict=True
		)

		if not employee_details:
			return

		approver_employee = None

		# 1. Reports to
		if employee_details.reports_to:
			approver_employee = employee_details.reports_to

		# 2. Site Supervisor
		if not approver_employee and employee_details.site:
			approver_employee = frappe.db.get_value("Operations Site", employee_details.site, "site_supervisor")

		# 3. Project Manager
		if not approver_employee and employee_details.project:
			approver_employee = frappe.db.get_value("Project", employee_details.project, "project_manager")

		if approver_employee:
			approver_user = frappe.db.get_value("Employee", approver_employee, "user_id")
			if approver_user and frappe.db.exists("User", approver_user):
				self.supervisor = approver_user
			else:
				self.supervisor = None

		# Set Operations Manager from the resignation document
		if self.employee_resignation:
			rsgn_om = frappe.db.get_value("Employee Resignation", self.employee_resignation, "operations_manager")
			if rsgn_om:
				self.operations_manager = rsgn_om

		# Set Offboarding Officer — first user with that role
		if not self.get("offboarding_officer"):
			from frappe.utils.user import get_users_with_role
			om_users = get_users_with_role("Offboarding Officer")
			if om_users:
				self.offboarding_officer = om_users[0]


@frappe.whitelist()
def get_batch_employees(doctype, txt, searchfield, start, page_len, filters):
	employee_resignation = filters.get('employee_resignation')
	if not employee_resignation:
		return []
		
	if not frappe.has_permission("Employee Resignation", doc=employee_resignation, ptype="read"):
		return []
	
	page_len = frappe.utils.cint(page_len) or 20
	start = frappe.utils.cint(start) or 0
	
	return frappe.db.sql("""
		select t1.employee, t1.employee_name
		from `tabEmployee Resignation Item` t1
		where t1.parent = %s and t1.employee like %s
		limit %s offset %s
	""", (employee_resignation, f"%%{txt}%%", page_len, start))
