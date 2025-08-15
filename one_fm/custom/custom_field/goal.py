def get_goal_custom_fields():
    return {
        "Goal": [
            {
                "fieldname": "department",
                "fieldtype": "Data",
                "insert_after": "end_date",
                "label": "Department",
                "fetch_from": "employee.department",
                "in_list_view": 1,
                "in_standard_filter": 1,
                "read_only": 1,
                "translatable": 1
            }
        ]
    }
