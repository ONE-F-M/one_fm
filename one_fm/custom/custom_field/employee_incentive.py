def get_employee_incentive_custom_fields():
    return {
        "Employee Incentive": [
            {
                "fieldname": "rewarded_by",
                "fieldtype": "Select",
                "insert_after": "currency",
                "label": "Rewarded By",
                "options": "\nPercentage of Monthly Wage\nNumber of Daily Wage",
                "reqd": 1,
                "translatable": 1
            },
            {
                "fieldname": "wage_factor",
                "fieldtype": "Float",
                "insert_after": "wage",
                "label": "Wage Factor",
                "depends_on": "rewarded_by"
            },
            {
                "fieldname": "wage",
                "fieldtype": "Currency",
                "insert_after": "rewarded_by",
                "label": "Wage",
                "depends_on": "rewarded_by",
                "read_only": 1
            }
        ]
    }
