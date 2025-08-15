def get_hr_settings_custom_fields():
    return {
        "HR Settings": [
            {
                "fieldname": "custom_hr_manager",
                "fieldtype": "Link",
                "insert_after": "retirement_age",
                "label": "HR Manager",
                "options": "User",
                "description": "User ID of current HR Manager."
            },
            {
                "fieldname": "payroll_notifications_email",
                "fieldtype": "Data",
                "insert_after": "payroll_settings",
                "label": "Payroll Notifications Email",
                "description": "All payroll related notifications will be forwarded to this email id.",
                "translatable": 1
            },
            {
                "label": "Annual Leave Threshold",
                "fieldname": "annual_leave_threshold",
                "insert_after": "auto_leave_encashment",
                "fieldtype": "Int",
                "default": "60",
                "description": "The minimum number of annual leave days an employee must accumulate before a leave acknowledgment form is automatically generated."
            }
        ]
    }
