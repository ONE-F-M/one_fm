def get_employee_advance_custom_fields():
    return {
        "Employee Advance": [
            {
                "fieldname": "recruitment_trip_request",
                "fieldtype": "Link",
                "insert_after": "status",
                "label": "Recruitment Trip Request",
                "options": "Recruitment Trip Request"
            }
        ]
    }
