import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from one_fm.custom.custom_field.hr_settings import get_hr_settings_custom_fields


def execute():
	"""Add the 'Default Absence Investigation HR Officer' field to HR Settings."""
	create_custom_fields(get_hr_settings_custom_fields(), update=True)
