def get_salary_structure_assignment_custom_fields():
    return {
        "Salary Structure Assignment": [
            {
                "fieldname": "indemnity_calculation_section",
                "fieldtype": "Section Break",
                "label": "Indemnity Calculation",
                "insert_after": "variable"
            },
            {
                "fieldname": "salary_structure_components",
                "fieldtype": "Table",
                "label": "Salary Structure Components",
                "insert_after": "indemnity_calculation_section",
                "options": "Salary Component Table"
            },
            {
                "fieldname": "section_break_18",
                "fieldtype": "Section Break",
                "label": "Indemnity Calculation",
                "insert_after": "salary_structure_components"
            },
            {
                "fieldname": "indemnity_amount",
                "fieldtype": "Currency",
                "label": "Indemnity Amount",
                "insert_after": "section_break_18"
            },
            {
                "fieldname": "leave_allocation_amount",
                "fieldtype": "Currency",
                "label": "Leave Allocation Amount",
                "insert_after": "indemnity_amount"
            }
        ]
    }
