def get_employee_checkin_properties():
    return [
        {
            "doctype": "Property Setter",
            "doc_type": "Employee Checkin",
            "doctype_or_field": "DocType",
            "property": "field_order",
            "property_type": "Data",
            "value": "[\"employee\", \"employee_name\", \"log_type\", \"shift\", \"late_entry\", \"early_exit\", \"column_break_4\", \"time\", \"date\", \"device_id\", \"skip_auto_attendance\", \"attendance\", \"shift_timings_section\", \"shift_start\", \"shift_end\", \"offshift\", \"column_break_vyyt\", \"shift_details\", \"shift_actual_start\", \"shift_actual_end\", \"shift_assignment\", \"operations_shift\", \"operations_site\", \"project\", \"company\", \"is_replaced\", \"replaced_employee_checkin\", \"column_break_15\", \"operations_role\", \"post_abbrv\", \"roster_type\", \"shift_type\", \"shift_permission\", \"actual_time\", \"employee_checkin_issue\", \"source\"]"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Employee Checkin",
            "doctype_or_field": "DocField",
            "field_name": "employee",
            "property": "read_only",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Employee Checkin",
            "doctype_or_field": "DocField",
            "field_name": "time",
            "property": "read_only",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Employee Checkin",
            "doctype_or_field": "DocField",
            "field_name": "skip_auto_attendance",
            "property": "read_only",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Employee Checkin",
            "doctype_or_field": "DocField",
            "field_name": "device_id",
            "property": "read_only",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Employee Checkin",
            "doctype_or_field": "DocField",
            "field_name": "fetch_geolocation",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Employee Checkin",
            "doctype_or_field": "DocField",
            "field_name": "shift_timings_section",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Employee Checkin",
            "doctype_or_field": "DocField",
            "field_name": "column_break_vyyt",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        }
    ]
