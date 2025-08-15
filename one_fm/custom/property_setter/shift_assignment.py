def get_shift_assignment_properties():
    return [
        {
            "doctype": "Property Setter",
            "doc_type": "Shift Assignment",
            "doctype_or_field": "DocType",
            "property": "field_order",
            "property_type": "Data",
            "value": '["employee", "employee_name", "custom_employment_type", "shift_type", "site", "project", "status", "shift_classification", "site_location", "employee_schedule", "is_replaced", "replaced_shift_assignment", "day_off_ot", "column_break_3", "company", "start_date", "end_date", "start_datetime", "end_datetime", "shift_request", "department", "shift", "amended_from", "operations_role", "post_abbrv", "roster_type", "site_request", "check_in_site", "column_break_19", "check_out_site", "post_type"]'
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Shift Assignment",
            "doctype_or_field": "DocField",
            "field_name": "shift_type",
            "property": "fetch_from",
            "property_type": "Small Text",
            "value": "shift.shift_type"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Shift Assignment",
            "doctype_or_field": "DocField",
            "field_name": "start_date",
            "property": "in_standard_filter",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Shift Assignment",
            "doctype_or_field": "DocField",
            "field_name": "end_date",
            "property": "in_list_view",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Shift Assignment",
            "doctype_or_field": "DocField",
            "field_name": "end_date",
            "property": "in_standard_filter",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Shift Assignment",
            "doctype_or_field": "DocField",
            "field_name": "employee",
            "property": "in_standard_filter",
            "property_type": "Check",
            "value": "1"
        }
    ]