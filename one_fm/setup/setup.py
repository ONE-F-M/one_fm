from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def after_install():
    create_custom_fields(get_custom_fields())

def get_custom_fields():
    custom_fields = {}
    custom_fields.update(get_email_template_custom_fields())
    return custom_fields

def get_email_template_custom_fields():
    return {
        "Email Template": [
            {
                "fieldname": "add_workflow_action_buttons_to_email",
                "fieldtype": "Check",
                "label": "Add Workflow Action Buttons to Email",
                "insert_after": "response",
                "default": 0
            },
        ]
    }