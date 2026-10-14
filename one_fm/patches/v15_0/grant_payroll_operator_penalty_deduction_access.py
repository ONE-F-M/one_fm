import frappe
from frappe.permissions import add_permission, update_permission_property


def execute():
	# The Penalty Deduction Lifecycle assigns "Resolve Payroll Error" to payroll, and completing
	# a task needs write access on the document.
	add_permission("Penalty Deduction", "Payroll Operator", 0)
	update_permission_property("Penalty Deduction", "Payroll Operator", 0, "write", 1)
