def get_attendance_request_properties():
    return [
    {
        "doctype": "Property Setter",
        "doc_type": "Attendance Request",
        "doctype_or_field": "DocType",
        "property": "field_order",
        "property_type": "Data",
        "value": "[\"workflow_state\", \"employee\", \"employee_name\", \"department\", \"update_request\", \"approver\", \"approver_name\", \"approver_user\", \"column_break_5\", \"company\", \"from_date\", \"to_date\", \"half_day\", \"half_day_date\", \"include_holidays\", \"shift\", \"reason_section\", \"reason\", \"column_break_4\", \"explanation\", \"amended_from\"]"
    },
    {
        "doctype": "Property Setter",
        "doc_type": "Attendance Request",
        "doctype_or_field": "DocField",
        "field_name": "half_day",
        "property": "read_only",
        "property_type": "Check",
        "value": "1"
    },
    {
        "doctype": "Property Setter",
        "doc_type": "Attendance Request",
        "doctype_or_field": "DocField",
        "field_name": "half_day",
        "property": "hidden",
        "property_type": "Check",
        "value": "1"
    },
    {
        "doctype": "Property Setter",
        "doc_type": "Attendance Request",
        "doctype_or_field": "DocField",
        "field_name": "explanation",
        "property": "reqd",
        "property_type": "Check",
        "value": "1"
    },
    {
        "doctype": "Property Setter",
        "doc_type": "Attendance Request",
        "doctype_or_field": "DocField",
        "field_name": "workflow_state",
        "property": "in_list_view",
        "property_type": "Check",
        "value": "1"
    },
    {
        "doctype": "Property Setter",
        "doc_type": "Attendance Request",
        "doctype_or_field": "DocField",
        "field_name": "to_date",
        "property": "in_list_view",
        "property_type": "Check",
        "value": "1"
    },
    {
        "doctype": "Property Setter",
        "doc_type": "Attendance Request",
        "doctype_or_field": "DocField",
        "field_name": "from_date",
        "property": "in_list_view",
        "property_type": "Check",
        "value": "1"
    },
    {
        "doctype": "Property Setter",
        "doc_type": "Attendance Request",
        "doctype_or_field": "DocField",
        "field_name": "employee",
        "property": "in_list_view",
        "property_type": "Check",
        "value": "1"
    },
    {
        "doctype": "Property Setter",
        "doc_type": "Attendance Request",
        "doctype_or_field": "DocField",
        "field_name": "employee_name",
        "property": "in_list_view",
        "property_type": "Check",
        "value": "1"
    },
    {
        "doctype": "Property Setter",
        "doc_type": "Attendance Request",
        "doctype_or_field": "DocField",
        "field_name": "reason",
        "property": "in_list_view",
        "property_type": "Check",
        "value": "0"
    },
    {
        "doctype": "Property Setter",
        "doc_type": "Attendance Request",
        "doctype_or_field": "DocField",
        "field_name": "employee",
        "property": "ignore_user_permissions",
        "property_type": "Check",
        "value": "1"
    }
]
