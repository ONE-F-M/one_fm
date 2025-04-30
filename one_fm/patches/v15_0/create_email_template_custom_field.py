from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    create_custom_fields({
        "Email Template": [
            {
                "fieldname": "add_workflow_action_buttons_to_email",
                "fieldtype": "Check",
                "label": "Add Workflow Action Buttons to Email",
                "insert_after": "response",
                "default": 0
            },
        ]
    })