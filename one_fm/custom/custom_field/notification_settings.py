def get_notification_settings_custom_fields():
    return {
        "Notification Settings": [
            {
                "fieldname": "custom_enable_employee_birthday_notification",
                "fieldtype": "Check",
                "insert_after": "custom_enable_work_anniversary_notification",
                "label": "Enable Employee Birthday Notification",
                "description": "If checked, this allows the user to be sent employee birthday reminders"
            },
            {
                "fieldname": "custom_enable_work_anniversary_notification",
                "fieldtype": "Check",
                "insert_after": "energy_points_system_notifications",
                "label": "Enable Work Anniversary Notification",
                "description": "If checked, this allows the user to be sent work anniversary reminders"
            }
        ]
    }
