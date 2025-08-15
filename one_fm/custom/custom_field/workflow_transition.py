def get_workflow_transition_custom_fields():
    return {
        "Workflow Transition": [
            {
                "fieldname": "allowed_user_field",
                "fieldtype": "Select",
                "label": "Allowed User Field",
                "insert_after": "allowed_user_id",
                "translatable": 1
            },
            {
                "fieldname": "allowed_user_id",
                "fieldtype": "Link",
                "label": "Allowed User ID",
                "insert_after": "column_break_5",
                "options": "User"
            },
            {
                "fieldname": "column_break_5",
                "fieldtype": "Column Break",
                "insert_after": "allow_self_approval"
            },
            {
                "fieldname": "custom_confirm_message",
                "fieldtype": "Data",
                "label": "Confirm Message",
                "insert_after": "custom_requires_frontend_input",
                "depends_on": "custom_confirm_transition",
                "description": "Transition Confirmation Message is Optional.",
                "translatable": 1
            },
            {
                "fieldname": "custom_confirm_transition",
                "fieldtype": "Check",
                "label": "Confirm Transition",
                "insert_after": "skip_creation_of_workflow_action"
            },
            {
                "fieldname": "custom_requires_frontend_input",
                "fieldtype": "Check",
                "label": "Requires Frontend Input",
                "insert_after": "custom_confirm_transition"
            },
            {
                "fieldname": "skip_creation_of_workflow_action",
                "fieldtype": "Check",
                "label": "Skip Creation of Workflow Action",
                "insert_after": "skip_multiple_action"
            },
            {
                "fieldname": "skip_multiple_action",
                "fieldtype": "Check",
                "label": "Skip Multiple Action",
                "insert_after": "allowed_user_field"
            }
        ]
    }
