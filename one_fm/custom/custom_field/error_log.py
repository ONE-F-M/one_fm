def get_error_log_custom_fields():
    return {
        "Error Log": [
            {
                "fieldname": "issue_log",
                "fieldtype": "Data",
                "insert_after": "error",
                "label": "Issue Log",
                "read_only": 1
            }
        ]
    }
