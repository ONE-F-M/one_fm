def get_attendance_properties():
    return [
        {
            "doctype": "Property Setter",
            "doc_type": "Attendance",
            "doctype_or_field": "DocType",
            "property": "field_order",
            "property_type": "Data",
            "value": "[\"attendance_details\", \"naming_series\", \"employee\", \"employee_name\", \"employment_type\", \"working_hours\", \"status\", \"leave_type\", \"leave_application\", \"column_break0\", \"attendance_date\", \"company\", \"department\", \"attendance_request\", \"details_section\", \"shift\", \"in_time\", \"out_time\", \"column_break_18\", \"late_entry\", \"early_exit\", \"section_break_17\", \"shift_assignment\", \"operations_shift\", \"site\", \"project\", \"timesheet\", \"column_break_21\", \"operations_role\", \"post_abbrv\", \"roster_type\", \"post_type\", \"sale_item\", \"day_off_ot\", \"attendance_comment\", \"comment\", \"references\", \"reference_doctype\", \"column_break_nahps\", \"reference_docname\", \"amended_from\"]"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Attendance",
            "doctype_or_field": "DocField",
            "field_name": "roster_type",
            "property": "in_standard_filter",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Attendance",
            "doctype_or_field": "DocField",
            "field_name": "working_hours",
            "property": "depends_on",
            "property_type": "Data"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Attendance",
            "doctype_or_field": "DocField",
            "field_name": "shift",
            "property": "read_only",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Attendance",
            "doctype_or_field": "DocField",
            "field_name": "shift",
            "property": "fetch_if_empty",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Attendance",
            "doctype_or_field": "DocField",
            "field_name": "shift",
            "property": "fetch_from",
            "property_type": "Small Text",
            "value": "shift_assignment.shift_type"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Attendance",
            "doctype_or_field": "DocField",
            "field_name": "attendance_date",
            "property": "in_standard_filter",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Attendance",
            "doctype_or_field": "DocField",
            "field_name": "status",
            "property": "options",
            "property_type": "Select",
            "value": "Present\nAbsent\nOn Leave\nHalf Day\nWork From Home\nDay Off\nClient Day Off\nHoliday\nOn Hold"
        }
    ]
