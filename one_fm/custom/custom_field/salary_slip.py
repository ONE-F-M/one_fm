def get_salary_slip_custom_fields():
    return {
        "Salary Slip": [
            {
                "fieldname": "justification_needed_on_deduction",
                "fieldtype": "Check",
                "label": "Justification Needed on Deduction",
                "description": "If Justification Needed on Deduction is True, Prepare Justification for PAM.\nDetails are in HR and Payroll Additional Settings",
                "insert_after": "base_total_deduction",
                "read_only": 1
            },
            {
                "fieldname": "payroll_type",
                "fieldtype": "Select",
                "label": "Payroll Type",
                "insert_after": "column_break_wyhp",
                "default": "Basic",
                "fetch_from": "payroll_entry.payroll_type",
                "options": "\nBasic\nOver-Time",
                "translatable": 1
            },
            {
                "fieldname": "has_multiple_salary_structure",
                "fieldtype": "Check",
                "label": "Has Multiple Salary Structure",
                "insert_after": "salary_structure",
                "read_only": 1
            },
            {
                "fieldname": "custom_salary_slip_details",
                "fieldtype": "Section Break",
                "label": "Salary Slip Details",
                "insert_after": "justification_needed_on_deduction",
                "collapsible": 1,
                "depends_on": "eval:doc.has_multiple_salary_structure"
            },
            {
                "fieldname": "custom_salary_component_detail",
                "fieldtype": "Table",
                "label": "Salary Component Detail",
                "insert_after": "custom_salary_slip_details",
                "options": "Salary Component Detail",
                "depends_on": "eval:doc.has_multiple_salary_structure"
            }
        ]
    }