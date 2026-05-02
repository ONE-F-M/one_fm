import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from one_fm.custom.custom_field.sales_invoice_item import get_sales_invoice_item_custom_fields
from one_fm.custom.property_setter.sales_invoice import get_sales_invoice_properties
from one_fm.setup.setup import add_property_setter

def execute():
    # Only create the custom fields that are newly added in this PR/story
    # (The others are already created but it's safe to run create_custom_fields on them anyway)
    create_custom_fields(get_sales_invoice_item_custom_fields())
    
    # Apply the property setter for collapsible taxes_section
    add_property_setter(get_sales_invoice_properties())
