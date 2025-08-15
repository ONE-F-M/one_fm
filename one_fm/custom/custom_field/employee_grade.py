def get_employee_grade_custom_fields():
    return {
        "Employee Grade": [
            {
                "fieldname": "one_fm_sb_salary_structure_details",
                "fieldtype": "Section Break",
                "insert_after": "default_salary_structure",
                "label": "ONE fm SB Salary Structure Details"
            },
            {
                "fieldname": "salary_structures",
                "fieldtype": "Table",
                "insert_after": "one_fm_sb_salary_structure_details",
                "label": "Salary Structures",
                "options": "Employee Grade Salary Structure"
            }
        ]
    }
