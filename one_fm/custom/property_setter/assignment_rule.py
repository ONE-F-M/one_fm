def get_assignment_rule_properties():
    return [
        {
            "doctype": "Property Setter",
            "doc_type": "Assignment Rule",
            "doctype_or_field": "DocType",
            "property": "field_order",
            "property_type": "Data",
            "value": "[\"document_type\", \"due_date_based_on\", \"priority\", \"disabled\", \"column_break_4\", \"description\", \"is_assignment_rule_with_workflow\", \"assignment_rules_section\", \"assign_condition\", \"column_break_6\", \"unassign_condition\", \"section_break_10\", \"close_condition\", \"sb\", \"assignment_days\", \"assign_to_users_section\", \"rule\", \"custom_routine_task\", \"field\", \"users\", \"last_user\"]"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Assignment Rule",
            "doctype_or_field": "DocField",
            "field_name": "rule",
            "property": "options",
            "property_type": "Select",
            "value": "Round Robin\nLoad Balancing\nBased on Field\nBased on Process Task"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Assignment Rule",
            "doctype_or_field": "DocField",
            "field_name": "users",
            "property": "depends_on",
            "property_type": "Data",
            "value": "eval:doc.rule != 'Based on Field' && doc.rule != 'Based on Process Task'"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Assignment Rule",
            "doctype_or_field": "DocField",
            "field_name": "users",
            "property": "mandatory_depends_on",
            "property_type": "Data",
            "value": "eval:doc.rule != 'Based on Field' && doc.rule != 'Based on Process Task'"
        }
    ]
