from one_fm.custom.custom_field.stock_entry import get_stock_entry_custom_fields
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    custom_fields = get_stock_entry_custom_fields()
    create_custom_fields(custom_fields)
    