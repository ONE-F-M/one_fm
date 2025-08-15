def get_payment_entry_reference_custom_fields():
    return {
        "Payment Entry Reference": [
            {
                "fieldname": "is_allocate",
                "fieldtype": "Check",
                "insert_after": "allocated_amount",
                "label": "Is Allocate",
                "hidden": 1,
                "columns": 1,
                "in_list_view": 1
            }
        ]
    }
