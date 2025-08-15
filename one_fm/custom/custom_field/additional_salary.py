def get_additional_salary_custom_fields():
    return {
        "Additional Salary": [
            {
                "fieldname": "section_001",
                "fieldtype": "Section Break",
                "insert_after": "type",
                "label": "",
            },
            {
                "fieldname": "notes",
                "fieldtype": "Text",
                "insert_after": "section_001",
                "label": "Notes",
            },
            {
                "fieldname": "pifss_monthly_deduction",
                "fieldtype": "Link",
                "options": "PIFSS Monthly Deduction",
                "insert_after": "employee_name",
                "label": "PIFSS Monthly Deduction",
            },
            {
                "label": "Leave Application",
                "fieldname": "leave_application",
                "insert_after": "salary_component",
                "fieldtype": "Link",
                "options": "Leave Application"
            }
        ]
	}
