def get_project_properties():
    return [
        {
            "property": "field_order",
            "property_type": "Data",
            "value": "[\"github_sync_id\", \"one_fm_project_code\", \"naming_series\", \"project_name\", \"project_name_in_arabic\", \"status\", \"project_type\", \"type\", \"is_active\", \"percent_complete_method\", \"percent_complete\", \"column_break_5\", \"project_template\", \"expected_start_date\", \"expected_end_date\", \"priority\", \"department\", \"project_image\", \"exempt_auto_employee_schedule\", \"custom_exclude_from_default_shift_checker\", \"customer_details\", \"customer\", \"column_break_14\", \"sales_order\", \"users_section\", \"users\", \"copied_from\", \"site_section_01\", \"section_break0\", \"notes\", \"section_break_18\", \"actual_start_date\", \"actual_time\", \"column_break_20\", \"actual_end_date\", \"project_details\", \"estimated_costing\", \"total_costing_amount\", \"total_expense_claim\", \"total_purchase_cost\", \"total_depreciation_expense\", \"company\", \"column_break_28\", \"total_sales_amount\", \"total_billable_amount\", \"total_billed_amount\", \"total_consumed_material_cost\", \"cost_center\", \"income_account\", \"margin\", \"gross_margin\", \"column_break_37\", \"per_gross_margin\", \"monitor_progress\", \"collect_progress\", \"holiday_list\", \"frequency\", \"from_time\", \"to_time\", \"first_email\", \"second_email\", \"daily_time_to_send\", \"day_to_send\", \"weekly_time_to_send\", \"column_break_45\", \"message\", \"contract_details\", \"contract_duration\", \"no_of_posts_as_per_contract\", \"account_manager\", \"manager_name\", \"column_break_64\", \"number_of_sites\", \"number_of_shifts\", \"number_of_posts\", \"has_overtime_rate\", \"overtime_rate\", \"poc_list\", \"contact_html\", \"poc\", \"custom_payroll_frequency\", \"custom_payroll_start_date\", \"custom_column_break_wla9l\", \"custom_payroll_end_date\"]",
            "doc_type": "Project",
            "doctype_or_field": "DocType"
        },
        {
            "property": "read_only_depends_on",
            "property_type": "Data",
            "value": "eval:doc.project_type == 'External'",
            "doc_type": "Project",
            "doctype_or_field": "DocField",
            "field_name": "expected_end_date"
        },
        {
            "property": "read_only_depends_on",
            "property_type": "Data",
            "value": "eval:doc.project_type == 'External'",
            "doc_type": "Project",
            "doctype_or_field": "DocField",
            "field_name": "expected_start_date"
        },
        {
            "property": "depends_on",
            "property_type": "Data",
            "value": "eval:doc.project_type==\"External\"",
            "doc_type": "Project",
            "doctype_or_field": "DocField",
            "field_name": "customer_details"
        },
        {
            "property": "autoname",
            "property_type": "Data",
            "value": "field:project_name",
            "doc_type": "Project",
            "doctype_or_field": "DocType"
        },
        {
            "property": "default",
            "property_type": "Text",
            "value": "PROJ-.####",
            "doc_type": "Project",
            "doctype_or_field": "DocField",
            "field_name": "naming_series"
        },
        {
            "property": "depends_on",
            "property_type": "Data",
            "value": "",
            "doc_type": "Project",
            "doctype_or_field": "DocField",
            "field_name": "customer"
        },
        {
            "property": "mandatory_depends_on",
            "property_type": "Data",
            "value": "eval:doc.project_type == 'External'",
            "doc_type": "Project",
            "doctype_or_field": "DocField",
            "field_name": "customer"
        },
        {
            "property": "read_only_depends_on",
            "property_type": "Data",
            "value": "eval: doc.percent_complete_method != \"Manual\"",
            "doc_type": "Project",
            "doctype_or_field": "DocField",
            "field_name": "percent_complete"
        },
        {
            "property": "mandatory_depends_on",
            "property_type": "Data",
            "value": "eval:['Internal',\"SCRUM Project\",'Personal Project'].includes(cur_frm.doc.project_type)",
            "doc_type": "Project",
            "doctype_or_field": "DocField",
            "field_name": "users"
        },
        {
            "property": "options",
            "property_type": "Text",
            "value": "PROJ-.####",
            "doc_type": "Project",
            "doctype_or_field": "DocField",
            "field_name": "naming_series"
        },
        {
            "property": "ignore_user_permissions",
            "property_type": "Check",
            "value": "1",
            "doc_type": "Project",
            "doctype_or_field": "DocField",
            "field_name": "account_manager"
        }
    ]
