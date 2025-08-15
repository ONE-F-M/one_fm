def get_employment_type_custom_fields():
    return {
        "Employment Type": [
            {
                "fieldname": "attendance_by_timesheet",
                "fieldtype": "Check",
                "insert_after": "employee_type_name",
                "label": "Attendance by Timesheet",
                "description": "If Attendance by Timesheet is checked, then the employee will not assign to any shift.",
                "allow_in_quick_entry": 1
            }
        ]
    }
