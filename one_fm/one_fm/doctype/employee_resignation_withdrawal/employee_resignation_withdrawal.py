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
				and old_doc.workflow_state in ["Accepted by Supervisor", "Rejected By Supervisor"]
				and self.workflow_state == "Approved"
			):
				# 1 & 2. Set Employee Resignation State and Workflow State to "Withdrawn"
				if self.employee_resignation:
					resignation = frappe.get_doc("Employee Resignation", self.employee_resignation)
					resignation.db_set("status", "Withdrawn")
					

					if frappe.db.has_column("Employee Resignation", "workflow_state"):
						resignation.db_set("workflow_state", "Withdrawn")
				
				# 3. Clear Relieving Date on Employee record
				if self.employee:
					frappe.db.set_value("Employee", self.employee, "relieving_date", None)
				
				# 4. Set Project Manpower Request to "Withdrawn" if it exists
				if self.employee_resignation and frappe.db.exists("DocType", "Project Manpower Request"):
					pmr_list = frappe.get_all(
						"Project Manpower Request",
						filters={"employee_resignation": self.employee_resignation},
						pluck="name"
					)
					for pmr_name in pmr_list:
						pmr = frappe.get_doc("Project Manpower Request", pmr_name)
						pmr.db_set("status", "Withdrawn")
						if frappe.db.has_column("Project Manpower Request", "workflow_state"):
							pmr.db_set("workflow_state", "Withdrawn")

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
				if not self.reason_for_rejection:
					frappe.throw(_("Please provide Reason for Rejection"))

	def set_approver(self):
		if not self.employee:
			return

		employee_details = frappe.db.get_value(
			"Employee", self.employee, ["reports_to", "site", "project"], as_dict=True
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
			if approver_user:
				self.supervisor = approver_user
