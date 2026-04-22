from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from one_fm.custom.custom_field.employee import get_employee_custom_fields

def execute():
	"""Add custom_subcontractor_name to Employee"""
	create_custom_fields(get_employee_custom_fields())
