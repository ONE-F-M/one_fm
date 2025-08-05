def get_project_custom_fields():
    return {
        "Project": [
            {
                "fieldname": "custom_exclude_from_default_shift_checker",
                "label": "Exclude from Default Shift Checker",
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
                "fieldname": "total_expense_claim",
                "label": "Total Expense Claim (via Expense Claims)",
                "fieldtype": "Currency",
                "insert_after": "total_costing_amount",
                "read_only": 1
            },
            {
                "fieldname": "exempt_auto_employee_schedule",
                "label": "Exempt Auto Employee Schedule",
                "fieldtype": "Check",
                "insert_after": "project_image"
            },
            {
                "fieldname": "has_overtime_rate",
                "label": "Has Overtime Rate",
                "fieldtype": "Check",
                "insert_after": "number_of_posts"
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
                "fieldname": "manager_name",
                "label": "Manager Name",
                "fieldtype": "Data",
                "fetch_from": "account_manager.employee_name",
                "insert_after": "account_manager",
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
                "insert_after": "manager_name"
            },
            {
                "fieldname": "account_manager",
                "label": "Project Manager",
                "fieldtype": "Link",
                "insert_after": "no_of_posts_as_per_contract",
                "options": "Employee",
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
