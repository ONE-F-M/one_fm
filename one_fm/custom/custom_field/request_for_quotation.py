def get_request_for_quotation_custom_fields():
    return {
        "Request for Quotation": [
            {
                "fieldname": "custom_request_for_material",
                "label": "Request for Material",
                "fieldtype": "Link",
                "insert_after": "amended_from",
                "options": "Request for Material",
                "read_only": 1
            },
            {
                "fieldname": "workflow_state",
                "label": "Workflow State",
                "fieldtype": "Link",
                "options": "Workflow State",
                "hidden": 1,
                "no_copy": 1,
                "allow_on_submit": 1
            }
        ]
    }
