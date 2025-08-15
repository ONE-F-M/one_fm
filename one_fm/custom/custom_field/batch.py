def get_batch_custom_fields():
    return {
        "Batch": [
            {
                "fieldname": "supplier_batch_id",
                "fieldtype": "Data",
                "insert_after": "supplier",
                "label": "Supplier Batch ID"
            }
        ]
    }
