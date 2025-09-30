import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    create_custom_fields({
        "HD Ticket": [
            {
                "fieldname": "custom_process",
                "fieldtype": "Link",
                "label": "Process",
                "insert_after": "cb00",
                "reqd": 1,
                "default": "Others", 
                "options": "Process"
                
            },
        ]
    } )


    frappe.get_doc({
        "doctype": "Property Setter",
        "doctype_or_field": "DocField",
        "doc_type": "HD Ticket",
        "field_name": "status",
        "property": "options",
        "value":"Draft\nOpen\nReplied\nOn Hold\nPending Deployment\nResolved\nClosed",
        "default_value": "Open",
        "is_system_generated": 0,
        "docstatus": 0
    }).insert(ignore_permissions=True)