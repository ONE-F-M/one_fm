def get_payroll_entry_custom_fields():
    return {
        "Payroll Entry": [
            {
                "fieldname": "custom_project_filter",
                "fieldtype": "Link",
                "insert_after": "custom_project_configuration",
                "label": "Project",
                "options": "Project",
                "depends_on": "eval:doc.custom_project_configuration==\"Specific Project\"",
                "mandatory_depends_on": "eval:doc.custom_project_configuration==\"Specific Project\""
            },
            {
                "fieldname": "custom_project_configuration",
                "fieldtype": "Select",
                "insert_after": "department",
                "label": "Project Configuration",
                "options": "\nAll External Projects\nSpecific Project",
                "translatable": 1
            },
            {
                "fieldname": "payroll_type",
                "fieldtype": "Select",
                "insert_after": "section_break_cypo",
                "label": "Payroll Type",
                "options": "\nBasic\nOver-Time",
                "translatable": 1
            },
            {
                "fieldname": "payment_purpose",
                "fieldtype": "Select",
                "insert_after": "company",
                "label": "Payment Purpose",
                "options": "01 - Salary\n02 - Allowance",
                "reqd": 1
            }
        ]
    }
