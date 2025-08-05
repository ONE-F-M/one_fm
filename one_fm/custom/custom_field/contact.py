def get_contact_custom_fields():
    return {
        "Contact": [
            {
                "fieldname": "one_fm_doc_contact_field",
                "fieldtype": "Data",
                "insert_after": "more_info",
                "label": "",
                "hidden": 1,
                "translatable": 1
            },
            {
                "fieldname": "one_fm_civil_id",
                "fieldtype": "Data",
                "insert_after": "email_id",
                "label": "CIVIL ID",
                "hidden": 0,
                "translatable": 1
            }
        ]
    }
