# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

EXEMPT_ROLES = {"HR User", "HR Manager", "System Manager"}


class EmployeeRecordUpdateRequest(Document):
	def validate(self):
		if self.is_new() or (self.docstatus == 0 and self.has_value_changed("employee")):
			self.validate_department_access()

	def validate_department_access(self):
		"""Users without an HR role may only request updates for employees of their own department."""
		user = frappe.session.user
		if user == "Administrator" or EXEMPT_ROLES.intersection(frappe.get_roles(user)):
			return

		# frappe.db, not get_list: the check must not depend on User Permissions.
		requester = frappe.db.get_value(
			"Employee", {"user_id": user, "status": "Active"}, ["name", "department"], as_dict=True
		)
		if not requester:
			frappe.throw(
				_(
					"Your user is not linked to an active Employee record. The HR User role is required to create an Employee Record Update Request."
				)
			)
		if not requester.department:
			frappe.throw(
				_(
					"Your Employee record has no Department. The HR User role is required to create an Employee Record Update Request."
				)
			)

		target_department = frappe.db.get_value("Employee", self.employee, "department")
		if not target_department:
			frappe.throw(
				_(
					"Employee {0} has no Department. The HR User role is required to create an Employee Record Update Request."
				).format(self.employee)
			)

		if requester.department != target_department:
			frappe.throw(
				_(
					"You are not allowed to create an Employee Record Update Request for an employee from a different department. The HR User role is required."
				)
			)
