import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from one_fm.custom.custom_field.error_log import get_error_log_custom_fields

def execute():
    create_custom_fields(get_error_log_custom_fields())
