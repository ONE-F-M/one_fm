def get_todo_custom_fields():
    """Return a dictionary of custom fields for the Employee document."""
    return {
        "ToDo": [
            {
                "fieldname": "notify_allocated_to_via_email",
                "fieldtype": "Check",
                "label": "Notify Allocated To Via Email",
                "insert_after": "allocated_to",
                "allow_in_quick_entry": 1
            },
            {
                "fieldname": "custom_column_break_x8z6v",
                "fieldtype": "Column Break",
                "label": "",
                "insert_after": "custom_google_task_title"
            },
            {
                "fieldname": "custom_google_task",
                "fieldtype": "Section Break",
                "label": "Google Task",
                "insert_after": "notify_allocated_to_via_email"
            },
            {
                "fieldname": "custom_google_task_id",
                "fieldtype": "Data",
                "label": "Google Task ID",
                "insert_after": "custom_column_break_x8z6v",
                "read_only": 1
            },
            {
                "fieldname": "custom_google_task_title",
                "fieldtype": "Data",
                "label": "Google Task Title",
                "insert_after": "custom_google_task",
                "read_only": 1
            },
            {
                "fieldname": "custom_source",
                "fieldtype": "Select",
                "label": "Source",
                "insert_after": "priority",
                "options": "ERP\nGoogle Task\nSpace",
                "default": "ERP",
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "type",
                "fieldtype": "Data",
                "label": "Type",
                "insert_after": "reference_name",
                "read_only": 1,
                "translatable": 1
            }
        ]
    }
