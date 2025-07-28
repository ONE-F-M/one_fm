def get_status_field_task_properties():
    return [
        {
            "doc_type": "Task",
            "doctype_or_field": "DocField",
            "field_name": "status",
            "property": "read_only",
            "property_type": "Check",
            "value": 0,
            "is_system_generated": 0
        }
    ]