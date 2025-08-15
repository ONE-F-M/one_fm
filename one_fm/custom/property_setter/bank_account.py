def get_bank_account_properties():
    return [
        {
            "doctype": "Property Setter",
            "doc_type": "Bank Account",
            "doctype_or_field": "DocField",
            "field_name": "bank_account_no",
            "property": "unique",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Bank Account",
            "doctype_or_field": "DocField",
            "field_name": "iban",
            "property": "unique",
            "property_type": "Check",
            "value": "1"
        }
    ]
