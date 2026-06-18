import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    custom_fields = {
        "HR Settings": [
            {
                "fieldname": "employee_status_update_notification_email_section",
                "fieldtype": "Section Break",
                "insert_after": "wiki_assessment_form_link",
                "label": "Employee Status Update Notification Email",
                "collapsible": 1,
            },
            {
                "fieldname": "employee_status_update_notification_members",
                "fieldtype": "Table",
                "insert_after": "employee_status_update_notification_email_section",
                "label": "Notification Members",
                "options": "ALM Notification Member",
            },
        ]
    }
    create_custom_fields(custom_fields)
