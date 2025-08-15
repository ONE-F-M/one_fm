def get_payroll_entry_properties():
    return [
        {
            "doc_type": "Payroll Entry",
            "doctype_or_field": "DocType",
            "property": "links_order",
            "property_type": "Small Text",
            "value": "[\"dcug485kh2\"]"
        },
        {
            "doc_type": "Payroll Entry",
            "doctype_or_field": "DocType",
            "property": "field_order",
            "property_type": "Data",
            "value": "[\"select_payroll_period\", \"posting_date\", \"company\", \"payment_purpose\", \"column_break_5\", \"currency\", \"exchange_rate\", \"payroll_payable_account\", \"status\", \"section_break_cypo\", \"payroll_type\", \"payroll_frequency\", \"start_date\", \"end_date\", \"column_break_13\", \"salary_slip_based_on_timesheet\", \"deduct_tax_for_unclaimed_employee_benefits\", \"deduct_tax_for_unsubmitted_tax_exemption_proof\", \"employees_tab\", \"section_break_17\", \"branch\", \"department\", \"custom_project_configuration\", \"custom_project_filter\", \"column_break_21\", \"designation\", \"grade\", \"number_of_employees\", \"section_break_24\", \"employees\", \"section_break_26\", \"validate_attendance\", \"attendance_detail_html\", \"accounting_dimensions_tab\", \"accounting_dimensions_section\", \"cost_center\", \"dimension_col_break\", \"project\", \"account\", \"payment_account\", \"column_break_35\", \"bank_account\", \"salary_slips_created\", \"salary_slips_submitted\", \"failure_details_section\", \"error_message\", \"section_break_41\", \"amended_from\", \"connections_tab\"]"
        },
        {
            "doc_type": "Payroll Entry",
            "doctype_or_field": "DocField",
            "field_name": "branch",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Payroll Entry",
            "doctype_or_field": "DocField",
            "field_name": "department",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Payroll Entry",
            "doctype_or_field": "DocField",
            "field_name": "designation",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Payroll Entry",
            "doctype_or_field": "DocField",
            "field_name": "grade",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Payroll Entry",
            "doctype_or_field": "DocField",
            "field_name": "payroll_frequency",
            "property": "options",
            "property_type": "select",
            "value": "\nMonthly"
        }
    ]
