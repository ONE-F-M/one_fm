def get_shift_request_properties():
    return [
        {
            "doc_type": "Shift Request",
            "doctype_or_field": "DocField",
            "field_name": "shift_type",
            "property": "mandatory_depends_on",
            "property_type": "Data",
            "value": "eval:doc.purpose != 'Assign Day Off';"
        },
        {
            "doc_type": "Shift Request",
            "doctype_or_field": "DocField",
            "field_name": "employee",
            "property": "ignore_user_permissions",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Shift Request",
            "doctype_or_field": "DocField",
            "field_name": "shift_type",
            "property": "read_only",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Shift Request",
            "doctype_or_field": "DocField",
            "field_name": "shift_type",
            "property": "depends_on",
            "property_type": "Data",
            "value": "eval:doc.purpose != 'Assign Day Off';"
        },
        {
            "doc_type": "Shift Request",
            "doctype_or_field": "DocField",
            "field_name": "shift_type",
            "property": "fetch_from",
            "property_type": "Small Text",
            "value": "operations_shift.shift_type"
        },
        {
            "doc_type": "Shift Request",
            "doctype_or_field": "DocField",
            "field_name": "approver",
            "property": "read_only",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Shift Request",
            "doctype_or_field": "DocField",
            "field_name": "approver",
            "property": "Hidden",
            "property_type": "check",
            "value": "1"
        },
        {
            "doc_type": "Shift Request",
            "doctype_or_field": "DocField",
            "field_name": "company",
            "property": "Hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Shift Request",
            "doctype_or_field": "DocField",
            "field_name": "shift_type",
            "property": "Hidden",
            "property_type": None,
            "value": "1"
        },
        {
            "doc_type": "Shift Request",
            "doctype_or_field": "DocField",
            "field_name": "approver",
            "property": "fetch_if_empty",
            "property_type": "Check",
            "value": "0"
        },
        {
            "doc_type": "Shift Request",
            "doctype_or_field": "DocField",
            "field_name": "approver",
            "property": "fetch_from",
            "property_type": "Small Text",
            "value": ""
        },
        {
            "doc_type": "Shift Request",
            "doctype_or_field": "DocField",
            "field_name": "company",
            "property": "read_only",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Shift Request",
            "doctype_or_field": "DocField",
            "field_name": "company",
            "property": "fetch_from",
            "property_type": "Small Text",
            "value": "employee.company"
        },
        {
            "doc_type": "Shift Request",
            "doctype_or_field": "DocField",
            "field_name": "status",
            "property": "read_only",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Shift Request",
            "doctype_or_field": "DocField",
            "field_name": "approver",
            "property": "ignore_user_permissions",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Shift Request",
            "doctype_or_field": "DocType",
            "property": "field_order",
            "property_type": "Data",
            "value": '["shift_type", "workflow_state", "title", "employee", "employee_name", "purpose", "replaced_employee", "custom_replaced_employee_name", "operations_shift", "shift", "site", "project", "department", "column_break_4", "company", "approver", "from_date", "to_date", "operations_role", "roster_type", "company_name", "shift_approver", "custom_shift_approvers", "update_request", "status", "amended_from", "site_request", "check_in_site", "checkin_longitude", "checkin_latitude", "checkin_radius", "checkin_map_html", "column_break_15", "check_out_site", "checkout_longitude", "checkout_latitude", "checkout_radius", "checkout_map_html", "checkout_map", "checkin_map"]'
        }
    ]
