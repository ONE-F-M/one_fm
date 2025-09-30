from one_fm.setup.setup import delete_custom_fields

def execute():
    custom_fields_to_remove = {
            "Error Log": [
                {
                    "fieldname": "issue_log",
                }
            ]
        }

    delete_custom_fields(custom_fields_to_remove)

