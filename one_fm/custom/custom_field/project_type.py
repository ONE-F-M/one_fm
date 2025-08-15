def get_project_type_custom_fields():
    return {
        "Project Type": [
            {
                "fieldname": "type",
                "fieldtype": "Select",
                "insert_after": "project_type",
                "label": "Type",
                "options": "\nSCRUM\nPersonal\nActive Repetitive",
                "translatable": 1,
                "allow_in_quick_entry": 1
            }
        ]
    }
