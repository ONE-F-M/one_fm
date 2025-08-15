def get_job_opening_properties():
    return [
        {
            "doctype": "Property Setter",
            "doc_type": "Job Opening",
            "property": "fetch_if_empty",
            "property_type": "Check",
            "field_name": "department",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Job Opening",
            "property": "fetch_from",
            "property_type": "Small Text",
            "field_name": "department",
            "value": "one_fm_erf.department"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Job Opening",
            "property": "fetch_if_empty",
            "property_type": "Check",
            "field_name": "designation",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Job Opening",
            "property": "fetch_from",
            "property_type": "Small Text",
            "field_name": "designation",
            "value": "one_fm_erf.designation"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Job Opening",
            "property": "search_fields",
            "property_type": "Data",
            "value": "designation, department, one_fm_erf"
        }
    ]
