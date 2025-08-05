def get_email_account_custom_fields():
    return {
        "Email Account": [
            {
                "fieldname": "default_helpdesk_outgoing_email_account",
                "fieldtype": "Check",
                "insert_after": "default_outgoing",
                "label": "Default Helpdesk Outgoing Email Account",
                "description": "If checked this email account will be used for all outgoing emails from the helpdesk."
            }
        ]
    }
