def get_supplier_quotation_custom_fields():
    return {
        "Supplier Quotation": [
            {
                "fieldname": "custom_request_for_quotation",
                "label": "Request for Quotation",
                "fieldtype": "Link",
                "insert_after": "amended_from",
                "options": "Request for Quotation",
                "read_only": 1
            },
            {
                "fieldname": "custom_request_for_material",
                "label": "Request for Material",
                "fieldtype": "Link",
                "insert_after": "custom_request_for_quotation",
                "options": "Request for Material",
                "read_only": 1
            }
        ]
    }
