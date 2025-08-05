def get_issue_properties():
    return [
        {
            "doctype_or_field": "DocField",
            "doc_type": "Issue",
            "field_name": "issue_type",
            "property": "allow_in_quick_entry",
            "property_type": "Check",
            "value": 1
        },
        {
            "doctype_or_field": "DocField",
            "doc_type": "Issue",
            "field_name": "issue_type",
            "property": "reqd",
            "property_type": "Check",
            "value": 1
        },
        {
            "doctype_or_field": "DocField",
            "doc_type": "Issue",
            "field_name": "naming_series",
            "property": "options",
            "property_type": "Text",
            "value": "ISS-.YYYY.-"
        }
    ]
