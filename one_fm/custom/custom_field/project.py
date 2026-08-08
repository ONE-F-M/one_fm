def get_project_custom_fields():
    return {
        "Project": [
            {
                "label": "Success Metrics",
                "fieldname": "custom_success_metrics",
                "insert_after": "custom_success_and_completion_criteria",
                "fieldtype": "Text",
                "description": "Define the metric of success",
            },
            {
                "label": "Milestones and Meeting Dates",
                "fieldname": "custom_milestones_and_meeting_dates",
                "insert_after": "custom_end_date",
                "fieldtype": "Table",
                "options": "Milestones and Meeting Dates",
            },
            {
                
                "label": "Project Communication",
                "fieldname": "custom_project_communication",
                "insert_after": "custom_meeting_frequency",
                "fieldtype": "Check",
                "description": "Make Sure to create a Google Chat or Google Space",
            },
            {
                "label": "Meeting Frequency",
                "fieldname": "custom_meeting_frequency",
                "insert_after": "custom_project_duration_weeks",
                "fieldtype": "Small Text",
            },
            {
                "label": "Success and Completion Criteria",
                "fieldname": "custom_success_and_completion_criteria",
                "insert_after": "custom_column_break_acgz2",
                "fieldtype": "Text",
                "description": "What signifies the project’s completion?",
            },
            {
    
                "label": "",
                "fieldname": "custom_column_break_acgz2",
                "insert_after": "custom_evidence_of_completion",
                "fieldtype": "Column Break",
            },
            
            {
                "label": "End Date",
                "fieldname": "custom_end_date",
                "insert_after": "custom_column_break_vf2fc",
                "fieldtype": "Date",
            },
            {
                "fieldname": "custom_column_break_vf2fc",
                "insert_after": "custom_project_duration_weeks",
                "fieldtype": "Column Break",
            },
            {
                "label": "Project Duration (Weeks)",
                "fieldname": "custom_project_duration_weeks",
                "insert_after": "custom_start_date",
                "fieldtype": "Data",
                "read_only": 1,
            },
            {
                "label": "Start Date",
                "fieldname": "custom_start_date",
                "insert_after": "custom_work_project_structure",
                "fieldtype": "Date",
            },
            {
                "label": "Work Project Structure",
                "fieldname": "custom_work_project_structure",
                "depends_on": "eval:doc.project_type == \"Internal\"",
                "fieldtype": "Section Break",
                "insert_after":"custom_success_metrics",
                "collapsible": 1,
            },
            {
                "label": "Evidence of Completion",
                "fieldname": "custom_evidence_of_completion",
                "insert_after": "custom_project_outcome",
                "fieldtype": "Attach",
                "description": "Attach document signifying project's completion",
            },
            {
                "label": "Project Outcome",
                "fieldname": "custom_project_outcome",
                "insert_after": "custom_project_outcome_summary",
                "fieldtype": "Text",
                "description": "This project must answer three questions: <br>Why are we doing this (its connection to company goals)?<br> What is the successful outcome we need (the Key Result)? <br> And how will we get there (the list of required stories/tasks)?",
            },
            {
                "label": "Project Outcome",
                "fieldname": "custom_section_break_xvhtn",
                "insert_after": "custom_exclude_from_default_shift_checker",
                "fieldtype": "Section Break",
                "collapsible": 1,
                "depends_on": "eval:doc.project_type == \"Internal\"",
            },
            {
                "fieldname": "custom_exclude_from_default_shift_checker",
                "label": "Exclude from Default Shift Checker",
                "depends_on": "eval:doc.project_type != \"Internal\"",
                "fieldtype": "Check",
                "description": "If set to True, all Employees allocated under this project will not be considered in Default Shift Checker.",
                "insert_after": "exempt_auto_employee_schedule"
            },
            {
                "fieldname": "custom_payroll_end_date",
                "label": "Payroll End Date",
                "fieldtype": "Select",
                "options": "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12\n13\n14\n15\n16\n17\n18\n19\n20\n21\n22\n23\n24\n25\n26\n27\n28\n29\n30\n31",
                "insert_after": "custom_column_break_wla9l",
                "translatable": 1
            },
            {
                "fieldname": "custom_column_break_wla9l",
                "label": "",
                "fieldtype": "Column Break",
                "insert_after": "custom_payroll_start_date"
            },
            {
                "fieldname": "custom_payroll_start_date",
                "label": "Payroll Start Date",
                "fieldtype": "Select",
                "options": "1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12\n13\n14\n15\n16\n17\n18\n19\n20\n21\n22\n23\n24\n25\n26\n27\n28\n29\n30\n31",
                "insert_after": "custom_payroll_frequency",
                "translatable": 1
            },
            {
                "fieldname": "custom_payroll_frequency",
                "label": "Payroll Frequency",
                "fieldtype": "Section Break",
                "depends_on": "eval:doc.project_type != \"Internal\"",
                "insert_after": "poc"
            },
            {
                "fieldname": "type",
                "label": "Type",
                "fieldtype": "Data",
                "fetch_from": "project_type.type",
                "insert_after": "project_type",
                "translatable": 1
            },
            {
                "fieldname": "custom_sprint_prefix",
                "label": "Sprint Prefix",
                "fieldtype": "Data",
                "insert_after": "type",
                # `doc.type` is the controlled Select fetched from Project Type;
                # the same test gates the users section / users field in
                # one_fm.custom.property_setter.project. Keep them identical.
                "depends_on": "eval:doc.type=='SCRUM'",
                "mandatory_depends_on": "eval:doc.type=='SCRUM'",
                "description": "Sprints for this project are named &lt;prefix&gt;-001, -002, … Keep it short and unique.",
            },
            {
                "fieldname": "total_expense_claim",
                "label": "Total Expense Claim (via Expense Claims)",
                "fieldtype": "Currency",
                "insert_after": "total_costing_amount",
                "read_only": 1
            },
            {
                "fieldname": "exempt_auto_employee_schedule",
                "depends_on": "eval:doc.project_type != \"Internal\"",
                "label": "Exempt Auto Employee Schedule",
                "fieldtype": "Check",
                "insert_after": "project_image"
            },
            {
                "fieldname": "has_overtime_rate",
                "label": "Has Overtime Rate",
                "fieldtype": "Check",
                "insert_after": "number_of_posts",
                "depends_on": "eval:doc.project_type == \"External\""
            },
            {
                "fieldname": "overtime_rate",
                "label": "Overtime Rate",
                "fieldtype": "Float",
                "depends_on": "eval:doc.has_overtime_rate==1",
                "description": "Overtime rate per hour",
                "insert_after": "has_overtime_rate",
                "precision": "3"
            },
            {
                "fieldname": "project_name_in_arabic",
                "depends_on": "eval:doc.project_type != \"Internal\"",
                "label": "Project Name In Arabic",
                "fieldtype": "Data",
                "insert_after": "project_name",
                "translatable": 1
            },
            {
                "fieldname": "total_depreciation_expense",
                "label": "Total Depreciation Expense",
                "fieldtype": "Currency",
                "insert_after": "total_purchase_cost",
                "options": "currency",
                "read_only": 1
            },
            {
                "fieldname": "income_account",
                "label": "Default Income Account",
                "fieldtype": "Link",
                "insert_after": "cost_center",
                "options": "Account"
            },
            {
                "fieldname": "one_fm_project_code",
                "label": "Project Code",
                "fieldtype": "Data",
                "insert_after": "github_sync_id",
                "hidden": 1
            },
            {
                "fieldname": "project_manager_name",
                "label": "Project Manager Name",
                "fieldtype": "Data",
                "fetch_from": "project_manager.employee_name",
                "insert_after": "project_manager",
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "contact_html",
                "label": "Contact Html",
                "fieldtype": "HTML",
                "insert_after": "poc_list"
            },
            {
                "fieldname": "poc",
                "label": "POC",
                "fieldtype": "Table",
                "insert_after": "contact_html",
                "options": "POC"
            },
            {
                "fieldname": "poc_list",
                "label": "POC List",
                "fieldtype": "Section Break",
                "depends_on": "eval:doc.project_type==\"External\"",
                "insert_after": "overtime_rate"
            },
            {
                "fieldname": "number_of_posts",
                "label": "Number of Posts",
                "fieldtype": "Int",
                "insert_after": "number_of_shifts"
            },
            {
                "fieldname": "number_of_shifts",
                "label": "Number of Shifts",
                "fieldtype": "Int",
                "insert_after": "number_of_sites"
            },
            {
                "fieldname": "number_of_sites",
                "label": "Number of Sites",
                "fieldtype": "Int",
                "insert_after": "column_break_64"
            },
            {
                "fieldname": "column_break_64",
                "fieldtype": "Column Break",
                "insert_after": "no_of_posts_as_per_contract"
            },
            {
                "fieldname": "project_manager",
                "label": "Project Manager",
                "fieldtype": "Link",
                "insert_after": "users_section",
                "options": "Employee",
                "ignore_user_permissions": 1,
                "mandatory_depends_on": "eval:doc.project_type==\"External\""
            },
            {
                "fieldname": "no_of_posts_as_per_contract",
                "label": "No of Posts as per Contract",
                "fieldtype": "Int",
                "insert_after": "contract_duration"
            },
            {
                "fieldname": "contract_duration",
                "label": "Contract Duration",
                "fieldtype": "Data",
                "insert_after": "contract_details",
                "translatable": 1
            },
            {
                "fieldname": "contract_details",
                "label": "Contract Details",
                "fieldtype": "Section Break",
                "depends_on": "eval:doc.project_type==\"External\"",
                "insert_after": "message"
            },
            {
                "fieldname": "site_section_01",
                "label": "Project Sites",
                "fieldtype": "Section Break",
                "collapsible": 1,
                "insert_after": "copied_from"
            },
            {
                "fieldname": "project_image",
                "label": "Project Image",
                "depends_on": "eval:doc.project_type != \"Internal\"",
                "fieldtype": "Attach Image",
                "insert_after": "department"
            },
            {
                "fieldname": "github_sync_id",
                "label": "GitHub Sync ID",
                "fieldtype": "Data",
                "hidden": 1,
                "read_only": 1,
                "unique": 1,
                "no_copy": 1
            }
        ]
    }
