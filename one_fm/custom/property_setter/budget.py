def get_budget_properties():
    return [
        {
            "doctype": "Property Setter",
            "doc_type": "Budget",
            "doctype_or_field": "DocType",
            "property": "quick_entry",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Budget",
            "doctype_or_field": "DocField",
            "field_name": "budget_against",
            "property": "options",
            "property_type": "Text",
            "value": "\nCost Center\nProject\n"
        }
    ]
