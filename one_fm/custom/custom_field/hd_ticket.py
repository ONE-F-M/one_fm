def get_hd_ticket_custom_fields():
    """Return a dictionary of custom fields for the Employee document."""
    return {
         "HD Ticket": [
            {
                "fieldname": "custom_ticket_category",
                "fieldtype": "Select",
                "label": "Ticket Category",
                "insert_after": "cb00",
                "reqd": 1,
                "options": "\nProcess Issue\nDoctype Issue\nFront End Issue\nMobile Issue\nOther Issues",
                "translatable": 0,
                "description": "Categorize the ticket. Selecting \"Process Issue\" reveals the mandatory Process field; selecting \"Doctype Issue\" reveals the mandatory Reference Doctype field."
            },
            {
                "fieldname": "custom_reference_doctype",
                "fieldtype": "Link",
                "label": "Reference Doctype",
                "insert_after": "custom_ticket_category",
                "options": "DocType",
                "depends_on": "eval: doc.custom_ticket_category == \"Doctype Issue\"",
                "mandatory_depends_on": "eval: doc.custom_ticket_category == \"Doctype Issue\""
            },
            {
                "fieldname": "custom_process",
                "fieldtype": "Link",
                "label": "Process",
                "insert_after": "custom_reference_doctype",
                "options": "Process",
                "depends_on": "eval: doc.custom_ticket_category == \"Process Issue\" || doc.custom_ticket_category == \"Doctype Issue\"",
                "mandatory_depends_on": "eval: doc.custom_ticket_category == \"Process Issue\"",
                "read_only_depends_on": "eval: doc.custom_ticket_category != \"Process Issue\""
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
                "fieldname": "custom_github_issue_url",
                "fieldtype": "Data",
                "label": "GitHub Issue",
                "insert_after": "custom_dev_ticket",
                "read_only": 1
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
            },
            {
                "fieldname": "planning_prompts_count",
                "fieldtype": "Int",
                "label": "Planning Prompts Count",
                "insert_after": "resolution_date",
                "depends_on": "eval:doc.ticket_type == 'Bug'"
            },
            {
                "fieldname": "execution_prompt_count",
                "fieldtype": "Int",
                "label": "Execution Prompt Count",
                "insert_after": "planning_prompts_count",
                "depends_on": "eval:doc.ticket_type == 'Bug'"
            },
            {
                "label": "Development Feedback",
                "fieldname": "development_feedback_sb",
                "insert_after": "feedback_extra",
                "fieldtype": "Section Break",
                "collapsible": 1,
            },
            {
                "label": "Developer Feedback",
                "fieldname": "developer_feedback",
                "insert_after": "development_feedback_sb",
                "fieldtype": "Small Text",
                "depends_on": "eval:doc.ticket_type=='Bug'",
                "mandatory_depends_on": "eval:doc.ticket_type==\"Bug\" && (doc.status == \"Closed\" || doc.status == \"Resolved\")",
                "translatable": 1,
            },
            {
                "fieldname": "column_break_banio",
                "insert_after": "developer_feedback",
                "fieldtype": "Column Break",
            },
            {
                "label": "Development Process Owner Remark",
                "fieldname": "development_process_owner_remark",
                "insert_after": "column_break_banio",
                "fieldtype": "Small Text",
                "depends_on": "eval:doc.ticket_type==\"Bug\" && (doc.status == \"Closed\" || doc.status == \"Resolved\")",
                "translatable": 1,
            }
        ]
    }
