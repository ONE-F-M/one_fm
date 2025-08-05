def get_gender_properties():
    return [
        {
            "doctype_or_field": "DocField",
            "doc_type": "Gender",
            "field_name": "gender",
            "property": "label",
            "property_type": "Data",
            "value": "Gender (ENGLISH)"
        },
        {
            "doctype_or_field": "DocField",
            "doc_type": "Gender",
            "field_name": "gender",
            "property": "unique",
            "property_type": "Check",
            "value": 1
        },
        {
            "doctype_or_field": "DocType",
            "doc_type": "Gender",
            "property": "field_order",
            "property_type": "Data",
            "value": "[\"gender\", \"gender_arabic\", \"maternity_required\"]"
        },
        {
            "doctype_or_field": "DocType",
            "doc_type": "Gender",
            "property": "quick_entry",
            "property_type": "Check",
            "value": 1
        }
    ]
