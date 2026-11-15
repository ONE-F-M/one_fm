# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

# Roles that see every HR Enquiry. Everyone else sees only the enquiries they are the
# subject or the issuer of. Only HR may set the decision: hr_decision is permlevel 1.
REVIEWER_ROLES = {"System Manager", "HR Manager", "HR User", "Legal Manager", "Legal User"}


class HREnquiry(Document):
	def before_insert(self):
		# The HR Enquiry Lifecycle assigns the HR Review to this user.
		if not self.hr_investigator:
			self.hr_investigator = frappe.db.get_single_value("Legal Settings", "hr_investigator")


def is_reviewer(user: str) -> bool:
	return user == "Administrator" or bool(REVIEWER_ROLES & set(frappe.get_roles(user)))


def get_permission_query_conditions(user: str | None = None) -> str:
	user = user or frappe.session.user
	if is_reviewer(user):
		return ""

	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	conditions = [f"`tabHR Enquiry`.`employee_user` = {frappe.db.escape(user)}"]
	if employee:
		conditions.append(f"`tabHR Enquiry`.`issuing_employee` = {frappe.db.escape(employee)}")
	return "(" + " or ".join(conditions) + ")"


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
	user = user or frappe.session.user
	if is_reviewer(user) or doc.employee_user == user:
		return True
	return bool(doc.issuing_employee) and doc.issuing_employee == frappe.db.get_value(
		"Employee", {"user_id": user}, "name"
	)
