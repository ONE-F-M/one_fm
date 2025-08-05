def get_customer_properties():
    return [
        {
            "doctype": "Property Setter",
            "doc_type": "Customer",
            "doctype_or_field": "DocField",
            "field_name": "customer_name",
            "property": "translatable",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Customer",
            "doctype_or_field": "DocField",
            "field_name": "naming_series",
            "property": "options",
            "property_type": "Text",
            "value": "CUST-.YYYY.-"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Customer",
            "doctype_or_field": "DocField",
            "field_name": "naming_series",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Customer",
            "doctype_or_field": "DocField",
            "field_name": "naming_series",
            "property": "reqd",
            "property_type": "Check",
            "value": "0"
        }
    ]
