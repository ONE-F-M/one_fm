def get_timesheet_custom_fields():
    return {
        "Timesheet": [
            {
                "fieldname": "approver",
                "fieldtype": "Link",
                "label": "Approver",
                "insert_after": "end_date",
                "options": "User"
            },
            {
                "fieldname": "salary_slip",
                "fieldtype": "Link",
                "label": "Salary Slip",
                "insert_after": "column_break_3",
                "options": "Salary Slip",
                "is_system_generated": 1,
                "no_copy": 1,
                "print_hide": 1,
                "read_only": 1
            },
            {
                "fieldname": "attendance_by_timesheet",
                "fieldtype": "Check",
                "label": "Attendance by Timesheet",
                "insert_after": "department",
                "fetch_from": "employee.attendance_by_timesheet",
                "hidden": 1
            }
        ]
    }