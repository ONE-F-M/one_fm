def get_company_custom_fields():
    return {
        "Company": [
            {
                "fieldname": "default_annual_leave_balance",
                "fieldtype": "Int",
                "insert_after": "default_holiday_list",
                "label": "Default Annual Leave Balance",
                "default": "30",
                "description": "Days"
            },
            {
                "fieldname": "company_name_arabic",
                "fieldtype": "Data",
                "insert_after": "company_name",
                "label": "Company Name Arabic",
                "translatable": 1
            },
            {
                "fieldname": "pifss_registration_no",
                "fieldtype": "Data",
                "insert_after": "company_name_arabic",
                "label": "PIFSS Registration no",
                "translatable": 1
            },
            {
                "fieldname": "live_user_notification",
                "fieldtype": "Section Break",
                "insert_after": "section_break_28",
                "label": "Live User Notification",
                "collapsible": 1
            },
            {
                "fieldname": "live_user_notification_message",
                "fieldtype": "Small Text",
                "insert_after": "live_user_notification",
                "label": "Live User Notification Message",
                "translatable": 1
            },
            {
                "fieldname": "notify",
                "fieldtype": "Table MultiSelect",
                "insert_after": "live_user_notification_message",
                "label": "Notify",
                "options": "Email Digest Recipient",
                "description": "Leave blank to notify all live users"
            },
            {
                "fieldname": "notify_live_users",
                "fieldtype": "Button",
                "insert_after": "notify",
                "label": "Notify Live Users"
            },
            {
                "fieldname": "column_break_107",
                "fieldtype": "Column Break",
                "insert_after": "notify_live_users"
            },
            {
                "fieldname": "last_notified",
                "fieldtype": "Small Text",
                "insert_after": "column_break_107",
                "label": "Last Notified",
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "last_notification_send_on",
                "fieldtype": "Datetime",
                "insert_after": "last_notified",
                "label": "Last Notification Send On",
                "read_only": 1
            },
            {
                "fieldname": "last_notification_send_by",
                "fieldtype": "Link",
                "insert_after": "last_notification_send_on",
                "label": "Last Notification Send By",
                "options": "User",
                "read_only": 1
            },
            {
                "fieldname": "last_notification_message",
                "fieldtype": "Small Text",
                "insert_after": "last_notification_send_by",
                "label": "Last Notification Message",
                "read_only": 1,
                "translatable": 1
            }
        ]
    }
