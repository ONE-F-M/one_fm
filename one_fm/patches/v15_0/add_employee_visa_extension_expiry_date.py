import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.employee import get_employee_custom_fields


def execute():
	"""Add custom_visa_extension_expiry_date to Employee.

	The definition in custom_field/employee.py is only applied by after_install.
	"""
	create_custom_fields(get_employee_custom_fields(), update=True)
	# Adds the column if an earlier ALTER failed: tabEmployee runs close to the row-size limit.
	frappe.db.updatedb("Employee")
