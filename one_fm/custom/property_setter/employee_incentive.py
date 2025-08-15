def get_employee_incentive_properties():
    return [
        {
            "doctype": "Property Setter",
            "doc_type": "Employee Incentive",
            "doctype_or_field": "DocField",
            "field_name": "company",
            "property": "read_only",
            "property_type": "Check",
            "value": "1"
        }
    ]
