def get_asset_movement_custom_fields():
    return {
        "Asset Movement": [
            {
                "fieldname": "delivery_receipt",
                "fieldtype": "Attach",
                "insert_after": "assets",
                "label": "Delivery Receipt"
            }
        ]
    }
