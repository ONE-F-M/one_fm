def get_email_template_custom_fields():
    return {
        "Email Template": [
            {
                "fieldname": "add_workflow_action_buttons_to_email",
                "fieldtype": "Check",
                "insert_after": "response",
                "label": "Add Workflow Action Buttons to Email",
                "default": "0"
            },
            {
                "fieldname": "applicable_module",
                "fieldtype": "Section Break",
                "insert_after": "email_reply_help",
                "label": "Applicable Module"
            },
            {
                "fieldname": "buying",
                "fieldtype": "Check",
                "insert_after": "selling",
                "label": "Buying"
            },
            {
                "fieldname": "hr",
                "fieldtype": "Check",
                "insert_after": "buying",
                "label": "HR"
            },
            {
                "fieldname": "selling",
                "fieldtype": "Check",
                "insert_after": "applicable_module",
                "label": "Selling"
            }
        ]
    }
