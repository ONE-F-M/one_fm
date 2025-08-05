def get_goal_properties():
    return [
        {
            "doctype_or_field": "DocField",
            "doc_type": "Goal",
            "field_name": "kra",
            "property": "read_only_depends_on",
            "property_type": "Data",
            "value": ""
        },
        {
            "doctype_or_field": "DocField",
            "doc_type": "Goal",
            "field_name": "kra",
            "property": "fetch_from",
            "property_type": "Small Text",
            "value": ""
        },
        {
            "doctype_or_field": "DocField",
            "doc_type": "Goal",
            "field_name": "employee",
            "property": "ignore_user_permissions",
            "property_type": "Check",
            "value": 1
        }
    ]
