def get_assignment_rule_custom_fields():
    return {
        "Assignment Rule": [
            {
                "fieldname": "custom_routine_task",
                "fieldtype": "Link",
                "insert_after": "disabled",
                "label": "Routine Task",
                "options": "Routine Task",
                "read_only": 1
            },
            {
                "fieldname": "is_assignment_rule_with_workflow",
                "fieldtype": "Check",
                "insert_after": "description",
                "label": "Is Assignment Rule with Workflow",
                "description": "Check true for getting action buttons for next workflow action in the assignment notification."
            }
        ]
    }
