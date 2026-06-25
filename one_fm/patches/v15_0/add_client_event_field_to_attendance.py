import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from one_fm.custom.custom_field.attendance import get_attendance_custom_fields

def execute():
	create_custom_fields(get_attendance_custom_fields())
