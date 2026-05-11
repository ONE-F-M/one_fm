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
            }
        ]
    }
