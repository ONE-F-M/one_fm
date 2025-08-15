def get_shift_type_properties():
    return [
        {
            "doc_type": "Shift Type",
            "doctype_or_field": "DocField",
            "field_name": "early_exit_grace_period",
            "property": "default",
            "property_type": "Text",
            "value": "0"
        },
        {
            "doc_type": "Shift Type",
            "doctype_or_field": "DocType",
            "property": "autoname",
            "property_type": "Data",
            "value": ""
        },
        {
            "doc_type": "Shift Type",
            "doctype_or_field": "DocType",
            "property": "quick_entry",
            "property_type": "Check",
            "value": "0"
        },
        {
            "doc_type": "Shift Type",
            "doctype_or_field": "DocType",
            "property": "search_fields",
            "property_type": "Data",
            "value": "start_time, end_time, duration"
        },
        {
            "doc_type": "Shift Type",
            "doctype_or_field": "DocField",
            "field_name": "end_time",
            "property": "fetch_from",
            "property_type": "Small Text",
            "value": ""
        },
        {
            "doc_type": "Shift Type",
            "doctype_or_field": "DocField",
            "field_name": "start_time",
            "property": "fetch_from",
            "property_type": "Small Text",
            "value": ""
        }
    ]