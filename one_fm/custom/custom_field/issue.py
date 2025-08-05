def get_issue_custom_fields():
    return {
        "Issue": [
            {
                "fieldname": "pivotal_tracker",
                "fieldtype": "Data",
                "insert_after": "content_type",
                "label": "Pivotal Tracker",
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "department",
                "fieldtype": "Link",
                "insert_after": "priority",
                "label": "Department",
                "options": "Department"
            },
            {
                "fieldname": "communication_medium",
                "fieldtype": "Select",
                "insert_after": "raised_by",
                "label": "Communication Medium",
                "options": "\nEmail\nWhatsApp\nMobile App\nSystem",
                "in_standard_filter": 1
            },
            {
                "label": "Your Issue Type",
                "fieldname": "your_issue_type",
                "insert_after": "issue_type",
                "fieldtype": "Data",
                "depends_on": "eval:doc.issue_type=='Other'",
                "description": "Mention your issue type here for adding to the Issue Type master "
            },
            {
                "label": "WhatsApp Number",
                "fieldname": "whatsapp_number",
                "insert_after": "communication_medium",
                "fieldtype": "Data",
                "depends_on": "eval:doc.communication_medium == 'WhatsApp'",
                "mandatory_depends_on": "eval:doc.communication_medium == 'WhatsApp'",
                "read_only": 1
            }
        ]
    }
