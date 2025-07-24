def get_assignment_rule_custom_fields():
    return {
        "Assignment Rule": [
            {
                "fieldname": "custom_routine_task",
                "fieldtype": "Link",
                "insert_after": "rule",
                "label": "Process Task",
                "options": "Process Task",
                "depends_on": "eval:doc.rule == \"Based on Process Task\"",
                "mandatory_depends_on": "eval:doc.rule == \"Based on Process Task\""
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
