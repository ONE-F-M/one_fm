def get_purchase_receipt_custom_fields():
    return {
        "Purchase Receipt": [
            {
                "fieldname": "one_fm_attach_delivery_note",
                "label": "Attach Stamped and Signed Delivery Note",
                "fieldtype": "Attach",
                "insert_after": "terms"
            }
        ]
    }
