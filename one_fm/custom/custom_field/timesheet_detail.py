def get_timesheet_detail_custom_fields():
    return {
        "Timesheet Detail": [
            {
                "fieldname": "site",
                "fieldtype": "Link",
                "label": "Site",
                "insert_after": "task",
                "options": "Operations Site"
            },
            {
                "fieldname": "shift",
                "fieldtype": "Link",
                "label": "Shift",
                "insert_after": "site",
                "options": "Operations Shift"
            },
            {
                "fieldname": "operations_role",
                "fieldtype": "Link",
                "label": "Operations Role",
                "insert_after": "project_details",
                "options": "Operations Role"
            }
        ]
    }