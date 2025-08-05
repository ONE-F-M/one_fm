def get_expense_claim_properties():
    return [
        {
            "doctype": "Property Setter",
            "doc_type": "Expense Claim",
            "doctype_or_field": "DocField",
            "field_name": "advances",
            "property": "permlevel",
            "property_type": "Int",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Expense Claim",
            "doctype_or_field": "DocField",
            "field_name": "payable_account",
            "property": "permlevel",
            "property_type": "Int",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Expense Claim",
            "doctype_or_field": "DocField",
            "field_name": "mode_of_payment",
            "property": "permlevel",
            "property_type": "Int",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Expense Claim",
            "doctype_or_field": "DocField",
            "field_name": "is_paid",
            "property": "permlevel",
            "property_type": "Int",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Expense Claim",
            "doctype_or_field": "DocField",
            "field_name": "approval_status",
            "property": "permlevel",
            "property_type": "Int",
            "value": "1"
        }
    ]
