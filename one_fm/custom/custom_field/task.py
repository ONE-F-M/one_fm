def get_task_custom_fields():
    return {
        "Task": [
            {
                "fieldname": "github_sync_id",
                "fieldtype": "Data",
                "insert_after": "project",
                "label": "GitHub Sync ID",
                "hidden": 1,
                "read_only": 1,
                "unique": 1
            },
            {
                "fieldname": "custom_project_type",
                "fieldtype": "Data",
                "insert_after": "github_sync_id",
                "label": "Project Type",
                "fetch_from": "project.project_type",
                "read_only": 1
            },
            {
                "fieldname": "custom_assigned_to",
                "fieldtype": "Table MultiSelect",
                "insert_after": "custom_project_type",
                "label": "Assigned To",
                "options": "Task Assignment"
            },
            {
                "fieldname": "is_routine_task",
                "fieldtype": "Check",
                "insert_after": "custom_assigned_to",
                "label": "Is Routine Task",
                "fetch_from": "type.is_routine_task",
                "read_only": 1
            },
            {
                "fieldname": "routine_erp_document",
                "fieldtype": "Link",
                "insert_after": "is_routine_task",
                "label": "Routine ERP Document",
                "options": "DocType",
                "depends_on": "eval:doc.is_routine_task",
                "read_only": 1
            },
            {
                "fieldname": "routine_erp_docname",
                "fieldtype": "Dynamic Link",
                "insert_after": "routine_erp_document",
                "label": "Routine ERP Docname",
                "options": "routine_erp_document",
                "depends_on": "eval:doc.is_routine_task",
                "read_only": 1
            },
            {
                "fieldname": "email_sender",
                "fieldtype": "Data",
                "insert_after": "routine_erp_docname",
                "label": "Email Sender"
            },
            {
                "fieldname": "auto_repeat",
                "fieldtype": "Link",
                "insert_after": "email_sender",
                "label": "Auto Repeat",
                "options": "Auto Repeat",
                "read_only": 1
            },
            {
                "fieldname": "total_expense_claim",
                "fieldtype": "Currency",
                "insert_after": "auto_repeat",
                "label": "Total Expense Claim",
                "fetch_from": "project.total_expense_claim",
                "fetch_if_empty": 1,
                "read_only": 1,
            },
            {
                "fieldname": "custom_reviewer",
                "fieldtype": "Link",
                "insert_after": "custom_assigned_to",
                "label": "Reviewer",
                "options": "User",
                "mandatory_depends_on": "custom_assigned_to",
                "default": "__user"
            }
        ]
    }
