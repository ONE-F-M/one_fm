def get_task_properties():
    return [
        {
            "doc_type": "Task",
            "doctype_or_field": "DocType",
            "property": "field_order",
            "property_type": "Data",
            "value": "[\"subject\", \"project\", \"github_sync_id\", \"custom_project_type\", \"custom_assigned_to\", \"is_routine_task\", \"routine_erp_document\", \"routine_erp_docname\", \"status\", \"column_break0\", \"priority\", \"exp_end_date\", \"expected_time\", \"auto_repeat\", \"section_break0\", \"description\", \"attachment\", \"image\", \"column_break1\", \"department\", \"company\", \"cost_center\", \"total_expense_claim\"]",
            "is_system_generated": 0
        },
        {
            "doc_type": "Task",
            "doctype_or_field": "DocField",
            "field_name": "type",
            "property": "allow_in_quick_entry",
            "property_type": "Check",
            "value": 1,
            "is_system_generated": 0
        },
        {
            "doc_type": "Task",
            "doctype_or_field": "DocType",
            "property": "allow_auto_repeat",
            "property_type": "Check",
            "value": 1,
            "is_system_generated": 0
        },
        {
            "doc_type": "Task",
            "doctype_or_field": "DocType",
            "property": "subject_field",
            "property_type": "Data",
            "value": "subject",
            "is_system_generated": 0
        },
        {
            "doc_type": "Task",
            "doctype_or_field": "DocType",
            "property": "email_append_to",
            "property_type": "Check",
            "value": 1,
            "is_system_generated": 0
        },
        {
            "doc_type": "Task",
            "doctype_or_field": "DocType",
            "property": "sender_field",
            "property_type": "Data",
            "value": "email_sender",
            "is_system_generated": 0
        },
        {
            "doc_type": "Task",
            "doctype_or_field": "DocField",
            "field_name": "status",
            "property": "read_only",
            "property_type": "Check",
            "value": 1,
            "is_system_generated": 0
        }
    ]
