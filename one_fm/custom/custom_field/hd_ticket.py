def get_hd_ticket_custom_fields():
    """Return a dictionary of custom fields for the Employee document."""
    return {
         "HD Ticket": [
            {
                "fieldname": "custom_process",
                "fieldtype": "Link",
                "label": "Process",
                "insert_after": "cb00",
                "reqd": 1,
                "default": "Others", 
                "options": "Process"
            },
            {
                "fieldname": "custom_dev_ticket",
                "fieldtype": "Data",
                "insert_after": "email_account",
                "label": "Dev Ticket",
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "custom_bug_buster",
                "fieldtype": "Link",
                "insert_after": "ticket_split_from",
                "label": "Bug Buster",
                "options": "User",
                "depends_on": "eval: doc.ticket_type == 'Bug'"
            },
            {
                "fieldname": "custom_process_owner",
                "fieldtype": "Link",
                "insert_after": "custom_process",
                "label": "Process Owner",
                "options": "User",
                "fetch_from": "custom_process.process_owner",
                "read_only": 1,
                "in_list_view": 1
            }
        ]
    }

