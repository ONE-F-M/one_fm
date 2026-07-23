def get_project_properties():
    return [
        {
            "doctype_or_field":"DocField",
            "doc_type":"Project",
            "field_name":"project_details",
            "property":"depends_on",
            "property_type":"Data",
            "value":"eval:doc.project_type!='Internal'",
        },
        {
            "doctype_or_field":"DocField",
            "doc_type":"Project",
            "field_name":"users_section",
            "property":"label",
            "property_type":"Data",
            "value":"Project Manager and Users"
        },
        {
            "doctype_or_field":"DocField",
            "doc_type":"Project",
            "field_name":"users_section",
            "property":"depends_on",
            "property_type":"Data",
            # Show the "Project Manager and Users" section for External, Internal,
            # and SCRUM projects (SCRUM already requires `users` via
            # mandatory_depends_on, so it must be visible for them too).
            "value":"eval:['External','Internal','SCRUM Project'].includes(doc.project_type)"
        },
        {
            "doctype_or_field":"DocField",
            "doc_type":"Project",
            "field_name":"monitor_progress",
            "property":"depends_on",
            "property_type":"Data",
            "value":"eval:doc.project_type != \"Internal\"",
            
        },
        { 
            
            "doctype_or_field":"DocType",
            "doc_type":"Project",
            "property":"quick_entry",
            "property_type":"Check",
            "value":"0",
            
        },
        {
            "doctype_or_field":"DocType",
            "doc_type":"Project",
            "property":"field_order",
            "property_type":"Data",
            "value":"[\"github_sync_id\", \"one_fm_project_code\", \"naming_series\", \"project_name\", \"project_name_in_arabic\", \"status\", \"project_type\", \"type\", \"is_active\", \"percent_complete_method\", \"percent_complete\", \"column_break_5\", \"project_template\", \"expected_start_date\", \"expected_end_date\", \"priority\", \"department\", \"project_image\", \"exempt_auto_employee_schedule\", \"custom_exclude_from_default_shift_checker\", \"custom_section_break_xvhtn\", \"custom_project_outcome\", \"custom_evidence_of_completion\", \"custom_column_break_acgz2\", \"custom_success_and_completion_criteria\", \"custom_work_project_structure\", \"custom_start_date\", \"custom_project_duration_weeks\", \"custom_meeting_frequency\", \"custom_project_communication\", \"custom_column_break_vf2fc\", \"custom_end_date\", \"custom_milestones\", \"custom_milestones_and_meeting_dates\", \"customer_details\", \"customer\", \"column_break_14\", \"sales_order\", \"users_section\", \"project_manager_name\", \"users\", \"custom_column_break_pn7fs\", \"project_manager\", \"copied_from\", \"section_break0\", \"notes\", \"section_break_18\", \"actual_start_date\", \"actual_time\", \"column_break_20\", \"actual_end_date\", \"project_details\", \"estimated_costing\", \"total_costing_amount\", \"total_expense_claim\", \"total_purchase_cost\", \"total_depreciation_expense\", \"company\", \"column_break_28\", \"total_sales_amount\", \"total_billable_amount\", \"total_billed_amount\", \"total_consumed_material_cost\", \"cost_center\", \"income_account\", \"margin\", \"gross_margin\", \"column_break_37\", \"per_gross_margin\", \"monitor_progress\", \"collect_progress\", \"holiday_list\", \"frequency\", \"from_time\", \"to_time\", \"first_email\", \"second_email\", \"daily_time_to_send\", \"day_to_send\", \"weekly_time_to_send\", \"column_break_45\", \"subject\", \"message\", \"contract_details\", \"contract_duration\", \"no_of_posts_as_per_contract\", \"column_break_64\", \"number_of_sites\", \"number_of_shifts\", \"number_of_posts\", \"has_overtime_rate\", \"overtime_rate\", \"poc_list\", \"contact_html\", \"poc\", \"custom_payroll_frequency\", \"custom_payroll_start_date\", \"custom_column_break_wla9l\", \"custom_payroll_end_date\"]"
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
        }
    ]
