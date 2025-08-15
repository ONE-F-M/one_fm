def get_notification_log_custom_fields():
    return {
        "Notification Log": [
            {
                "fieldname": "one_fm_mobile_app",
                "fieldtype": "Check",
                "insert_after": "open_reference_document",
                "label": "Mobile App",
                "default": "0"
            },
            {
                "fieldname": "category",
                "fieldtype": "Data",
                "insert_after": "from_user",
                "label": "Category",
                "translatable": 1
            },
            {
                "fieldname": "title",
                "fieldtype": "Text",
                "read_only": 1,
                "label": "Title"
            }
        ]
    }
