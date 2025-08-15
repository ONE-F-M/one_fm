def get_department_custom_fields():
    return {
        "Department": [
            {
                "fieldname": "department_code",
                "fieldtype": "Data",
                "insert_after": "department_name",
                "label": "Department Code",
                "reqd": 1,
                "hidden": 0,
                "in_list_view": 0,
                "in_standard_filter": 0
            },
            {
                "fieldname": "issue_types",
                "fieldtype": "Table",
                "insert_after": "issue_responder_role",
                "label": "Issue Types",
                "options": "Department Issue Type",
                "hidden": 0,
                "in_list_view": 0,
                "in_standard_filter": 0
            },
            {
                "fieldname": "issue_settings",
                "fieldtype": "Section Break",
                "insert_after": "old_parent",
                "label": "Issue Settings",
                "collapsible": 1,
                "hidden": 0,
                "in_list_view": 0,
                "in_standard_filter": 0
            },
            {
                "fieldname": "issue_responder_role",
                "fieldtype": "Link",
                "insert_after": "issue_settings",
                "label": "Issue Responder Role",
                "options": "Role",
                "hidden": 0,
                "in_list_view": 0,
                "in_standard_filter": 0
            }
        ]
    }
