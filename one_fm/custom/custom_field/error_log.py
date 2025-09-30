def get_error_log_custom_fields():
    return {
        "Error Log": [
            {
                "fieldname": "hd_ticket",
                "fieldtype": "Link",
                "insert_after": "error",
                "label": "HD Ticket",
                "read_only": 1,
                "options": "HD Ticket"
            }
        ]
    }

