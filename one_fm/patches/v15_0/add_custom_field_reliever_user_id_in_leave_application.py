import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    custom_fields = {
        "Leave Application": [
            {
                "fieldname": "reliever_user_id",
                "fieldtype": "Link",
                "insert_after": "reliever_employee_id",
                "label": "Reliever User ID",
                "options": "User",
                "fetch_from": "custom_reliever_.user_id",
                "read_only": 1
            }
        ]
    }
    create_custom_fields(custom_fields)
