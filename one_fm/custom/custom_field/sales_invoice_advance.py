def get_sales_invoice_advance_custom_fields():
    return {
        "Sales Invoice Advance": [
            {
                "fieldname": "custom_received_amount",
                "fieldtype": "Currency",
                "insert_after": "col_break1",
                "label": "Received Amount",
                "read_only": 1
            }
        ]
    }