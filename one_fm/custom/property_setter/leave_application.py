def get_leave_application_properties():
    return [
        {
            "doctype": "Property Setter",
            "doc_type": "Leave Application",
            "property": "read_only_depends_on",
            "property_type": "Data",
            "field_name": "description",
            "value": "eval:doc.workflow_state=='Open' || doc.workflow_state=='Approved' || doc.workflow_state=='Rejected'"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Leave Application",
            "property": "ignore_user_permissions",
            "property_type": "Check",
            "field_name": "employee",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Leave Application",
            "property": "read_only_depends_on",
            "property_type": "Data",
            "field_name": "employee",
            "value": ""
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Leave Application",
            "property": "default",
            "property_type": "Text",
            "field_name": "follow_via_email",
            "value": "0"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Leave Application",
            "property": "read_only_depends_on",
            "property_type": "Data",
            "field_name": "from_date",
            "value": ""
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Leave Application",
            "property": "read_only_depends_on",
            "property_type": "Data",
            "field_name": "half_day",
            "value": "eval:doc.workflow_state=='Open' || doc.workflow_state=='Approved' || doc.workflow_state=='Rejected'"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Leave Application",
            "property": "fetch_from",
            "property_type": "Small Text",
            "field_name": "leave_approver_name",
            "value": "leave_approver.full_name"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Leave Application",
            "property": "options",
            "property_type": "Text",
            "field_name": "leave_approver_name",
            "value": ""
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Leave Application",
            "property": "default",
            "property_type": "Text",
            "field_name": "leave_approver",
            "value": "Administrator"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Leave Application",
            "property": "read_only_depends_on",
            "property_type": "Data",
            "field_name": "leave_approver",
            "value": ""
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Leave Application",
            "property": "read_only_depends_on",
            "property_type": "Data",
            "field_name": "leave_type",
            "value": ""
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Leave Application",
            "property": "field_order",
            "property_type": "Data",
            "value": "[\"workflow_state\", \"naming_series\", \"employee\", \"employee_name\", \"column_break_4\", \"leave_type\", \"is_proof_document_required\", \"proof_document\", \"proof_documents\", \"company\", \"department\", \"section_break_5\", \"from_date\", \"to_date\", \"resumption_date\", \"half_day\", \"half_day_date\", \"total_leave_days\", \"custom_reason_for_cancel\", \"column_break1\", \"custom_propose_from_date\", \"custom_propose_to_date\", \"custom_total_propose_leave_days\", \"description\", \"leave_balance\", \"section_break_7\", \"leave_approver\", \"leave_approver_name\", \"follow_via_email\", \"column_break_18\", \"posting_date\", \"status\", \"custom_default_leave_application_operator\", \"sb_other_details\", \"salary_slip\", \"color\", \"custom_reliever_\", \"custom_reliever_name\", \"column_break_17\", \"letter_head\", \"amended_from\", \"custom_is_paid\", \"source\", \"custom_section_break_neyf8\", \"custom_reassigned_documents\"]"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Leave Application",
            "property": "max_attachments",
            "property_type": "Int",
            "value": "5"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Leave Application",
            "property": "options",
            "property_type": "Text",
            "field_name": "naming_series",
            "value": "HR-LAP-.YYYY.-"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Leave Application",
            "property": "read_only",
            "property_type": "Check",
            "field_name": "status",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Leave Application",
            "property": "read_only_depends_on",
            "property_type": "Data",
            "field_name": "status",
            "value": ""
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Leave Application",
            "property": "read_only",
            "property_type": "Check",
            "field_name": "to_date",
            "value": "1"
        },
        {
            "doctype": "Property Setter",
            "doc_type": "Leave Application",
            "property": "read_only_depends_on",
            "property_type": "Data",
            "field_name": "to_date",
            "value": ""
        }
    ]
