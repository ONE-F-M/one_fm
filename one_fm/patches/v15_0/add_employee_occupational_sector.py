from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from one_fm.custom.custom_field.employee import get_employee_custom_fields


def execute():
	"""WI-002745: add custom_occupational_sector to Employee.

	The definition in custom_field/employee.py is only applied by after_install, so on a
	site that is already installed a new entry in it never reaches the form.
	"""
	create_custom_fields(get_employee_custom_fields(), update=True)
