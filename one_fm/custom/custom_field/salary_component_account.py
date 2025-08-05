def get_salary_component_account_custom_fields():
    return {
        "Salary Component Account": [
            {
                "fieldname": "custom_department",
                "fieldtype": "Link",
                "label": "Department",
                "description": "If left empty, will apply to all departments.",
                "insert_after": "account",
                "options": "Department",
                "in_list_view": 1,
                "in_preview": 1,
                "in_standard_filter": 1
            }
        ]
    }
