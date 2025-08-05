def get_delivery_note_item_custom_fields():
    return {
        "Delivery Note Item": [
            {
                "fieldname": "site",
                "fieldtype": "Link",
                "insert_after": "target_warehouse",
                "label": "Site",
                "options": "Operations Site"
            },
            {
                "label": "Request for Material Item",
                "fieldname": "request_for_material_item",
                "insert_after": "material_request_item",
                "fieldtype": "Data"
            },
            {
                "label": "Request for Material",
                "fieldname": "request_for_material",
                "insert_after": "material_request",
                "fieldtype": "Link",
                "options": "Request for Material"
            }
        ]
    }
