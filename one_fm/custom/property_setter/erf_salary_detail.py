def get_erf_salary_detail_properties():
    return [
        {
            "doctype": "Property Setter",
            "doc_type": "ERF Salary Detail",
            "doctype_or_field": "DocField",
            "field_name": "amount",
            "property": "allow_on_submit",
            "property_type": "Check",
            "value": "0"
        }
    ]
