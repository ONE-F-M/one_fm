# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


class FormalHearing(Document):
	def has_not_attended_at_all(self):
		return not self.did_not_attend_first_hearing and not self.did_not_attend_rescheduled_hearing

	def before_save(self):
		# Automatically bypass Pending Operation Manager if the employee hasn't attended at all
		if self.workflow_state == "Pending Operation Manager" and self.has_not_attended_at_all():
			self.workflow_state = "Pending HR Manager"


@frappe.whitelist()
def make_leave_application(source_name: str, leave_type: str | None = None):
	def set_missing_values(source, target):
		if leave_type:
			target.leave_type = leave_type
		target.employee = source.employee
		target.posting_date = frappe.utils.today()
		
		# Map employee details explicitly
		employee = frappe.get_doc("Employee", source.employee)
		target.department = employee.department
		target.company = employee.company

	doc = get_mapped_doc("Formal Hearing", source_name, {
		"Formal Hearing": {
			"doctype": "Leave Application",
			"field_map": {
				"employee": "employee"
			}
		}
	}, target_doc=None, postprocess=set_missing_values)

	return doc


@frappe.whitelist()
def make_employee_resignation(source_name: str):
	def set_missing_values(source, target):
		target.employee = source.employee
		target.relieving_date = frappe.utils.today()
		# Add more mappings as needed from Employee details if not auto-fetched
		employee = frappe.get_doc("Employee", source.employee)
		target.department = employee.department
		target.designation = employee.designation
		target.employment_type = employee.employment_type
		target.company = employee.company

	doc = get_mapped_doc("Formal Hearing", source_name, {
		"Formal Hearing": {
			"doctype": "Employee Resignation",
			"field_map": {
				"employee": "employee"
			}
		}
	}, target_doc=None, postprocess=set_missing_values)

	return doc


@frappe.whitelist()
def make_employee_transfer(source_name: str):
	def set_missing_values(source, target):
		target.employee = source.employee
		target.transfer_date = frappe.utils.today()
		# Company is often required
		employee = frappe.get_doc("Employee", source.employee)
		target.company = employee.company

	doc = get_mapped_doc("Formal Hearing", source_name, {
		"Formal Hearing": {
			"doctype": "Employee Transfer",
			"field_map": {
				"employee": "employee"
			}
		}
	}, target_doc=None, postprocess=set_missing_values)

	return doc
