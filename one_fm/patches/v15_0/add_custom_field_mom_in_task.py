import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from one_fm.custom.custom_field.task import get_task_custom_fields

def execute():
    create_custom_fields(get_task_custom_fields())
