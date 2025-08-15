def get_shift_type_custom_fields():
    return {
        "Shift Type": [
            {
                "fieldname": "shift_type",
                "fieldtype": "Select",
                "label": "Shift Type",
                "insert_after": "shift_work",
                "options": "Morning\nAfternoon\nEvening\nDay\nNight",
                "depends_on": "eval:doc.shift_work==1",
                "translatable": 1
            },
            {
                "fieldname": "duration",
                "fieldtype": "Float",
                "label": "Duration",
                "insert_after": "edit_start_time_and_end_time",
                "description": "In hours"
            },
            {
                "fieldname": "employee_checkin_settings",
                "fieldtype": "Section Break",
                "label": "Employee Checkin Settings",
                "insert_after": "early_exit_grace_period"
            },
            {
                "fieldname": "notification_reminder_after_shift_start",
                "fieldtype": "Int",
                "label": "Notification reminder after shift start(in minutes)",
                "insert_after": "employee_checkin_settings"
            },
            {
                "fieldname": "supervisor_reminder_shift_start",
                "fieldtype": "Int",
                "label": "Supervisor reminder Shift Start",
                "insert_after": "notification_reminder_after_shift_start",
                "description": "Supervisor will receive Final Reminder for Check-in After Shift Starts"
            },
            {
                "fieldname": "column_break_25",
                "fieldtype": "Column Break",
                "insert_after": "supervisor_reminder_shift_start"
            },
            {
                "fieldname": "notification_reminder_after_shift_end",
                "fieldtype": "Int",
                "label": "Notification reminder after shift end",
                "insert_after": "column_break_25",
                "description": "Employee will receive Final Reminder for Check-in After Shift Ends"
            },
            {
                "fieldname": "supervisor_reminder_start_ends",
                "fieldtype": "Int",
                "label": "Supervisor Reminder Start Ends",
                "insert_after": "notification_reminder_after_shift_end",
                "description": "Supervisor will receive Final Reminder for Check-in After Shift Ends"
            },
            {
                "fieldname": "split_shift",
                "fieldtype": "Section Break",
                "label": "Split Shift",
                "insert_after": "shift_type"
            },
            {
                "fieldname": "has_split_shift",
                "fieldtype": "Check",
                "label": "Has Split Shift",
                "insert_after": "second_shift_start_time"
            },
            {
                "fieldname": "split_shift_time",
                "fieldtype": "Section Break",
                "label": "Split Shift Time",
                "insert_after": "has_split_shift",
                "collapsible": 1
            },
            {
                "fieldname": "first_shift_start_time",
                "fieldtype": "Time",
                "label": "First Shift Start Time",
                "insert_after": "split_shift",
                "fetch_from": "doc.start_time",
                "depends_on": "has_split_shift"
            },
            {
                "fieldname": "column_break_12",
                "fieldtype": "Column Break",
                "insert_after": "split_shift_time"
            },
            {
                "fieldname": "first_shift_end_time",
                "fieldtype": "Time",
                "label": "First Shift End Time",
                "insert_after": "column_break_12",
                "depends_on": "has_split_shift"
            },
            {
                "fieldname": "second_shift_end_time",
                "fieldtype": "Time",
                "label": "Second Shift End Time",
                "insert_after": "first_shift_end_time",
                "depends_on": "has_split_shift"
            },
            {
                "fieldname": "second_shift_start_time",
                "fieldtype": "Time",
                "label": "Second Shift Start Time",
                "insert_after": "first_shift_start_time",
                "depends_on": "has_split_shift"
            },
            {
                "fieldname": "deadline",
                "fieldtype": "Check",
                "label": "Deadline",
                "insert_after": "late_entry_grace_period",
                "description": "Mark Absent if the employee doesn't check in before a given time."
            },
            {
                "fieldname": "shift_work",
                "fieldtype": "Check",
                "label": "Shift Work",
                "insert_after": "enable_auto_attendance",
                "default": "1",
                "description": "Will the employee(s) work in a shift based job assignment"
            },
            {
                "fieldname": "edit_start_time_and_end_time",
                "fieldtype": "Check",
                "label": "Edit Start Time and End Time",
                "insert_after": "end_time",
                "depends_on": "eval:!doc.__islocal"
            }
        ]
    }
