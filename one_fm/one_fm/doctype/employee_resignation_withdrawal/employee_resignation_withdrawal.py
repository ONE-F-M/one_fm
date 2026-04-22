# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class EmployeeResignationWithdrawal(Document):
	def on_update(self):
		self.validate_rejection_reason()
		self.process_withdrawal_approval()

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
							
							# A. Clear Relieving Date on the actual Employee profile
							if row.employee:
								frappe.db.set_value("Employee", row.employee, "relieving_date", None)
								
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
							
							will_withdraw = False
							
							# If ENTIRE roster is withdrawn, gracefully flag the PMR status
							if total_withdrawn_count >= total_in_batch:
								will_withdraw = True
							
							# Save document structurally so math functions natively resolve
							# Note: We do NOT set workflow_state before save to avoid native transition blocks
							pmr.save(ignore_permissions=True)
							
							# Manually force workflow override behind the back of validation to Cancelled
							if will_withdraw and frappe.db.has_column("Project Manpower Request", "workflow_state"):
							    pmr.db_set("workflow_state", "Cancelled")
					
					# Step 3: Flag Parent Resignation if entirely withdrawn
					if total_withdrawn_count >= total_in_batch:
						# All employees withdrawn, mark parent as Withdrawn
						resignation.db_set("status", "Withdrawn")
						if frappe.db.has_column("Employee Resignation", "workflow_state"):
							resignation.db_set("workflow_state", "Withdrawn")

	def validate(self):
		self.set_approver()

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
				if frappe.db.has_column("Employee Resignation Withdrawal", "supervisor"):
				    self.supervisor = approver_user
			else:
			    if frappe.db.has_column("Employee Resignation Withdrawal", "supervisor"):
			        self.supervisor = None


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
