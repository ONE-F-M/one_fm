def get_employee_advance_properties():
    return [
        {
            "doctype": "Property Setter",
            "doc_type": "Employee Advance",
            "doctype_or_field": "DocField",
            "field_name": "repay_unclaimed_amount_from_salary",
            "property": "permlevel",
            "property_type": "Int",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Employee Advance",
            "doctype_or_field": "DocField",
            "field_name": "mode_of_payment",
            "property": "permlevel",
            "property_type": "Int",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Employee Advance",
            "doctype_or_field": "DocField",
            "field_name": "advance_account",
            "property": "permlevel",
            "property_type": "Int",
            "value": "1"
        }
    ]
