import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    custom_fields = {
        "HR Settings": [
            {
                "fieldname": "attendance_check_action_user",
                "fieldtype": "Link",
                "insert_after": "custom_hr_manager",
                "label": "Attendance Check Action User",
                "options": "User",
                "description": "Default Action Owner. Auto-populated into the 'Assigned To' field of every auto-generated Attendance Check Action.",
            },
        ]
    }
    create_custom_fields(custom_fields)
