def get_purchase_receipt_custom_fields():
    return {
        "Purchase Receipt": [
            {
                "fieldname": "one_fm_attach_delivery_note",
                "label": "Attach Stamped and Signed Delivery Note",
                "fieldtype": "Attach",
                "insert_after": "terms"
            },
            {
                "label": "Request for Purchase",
                "fieldname": "custom_request_for_purchase",
                "insert_after": "set_posting_time",
                "fieldtype": "Link",
                "options": "Request for Purchase",
                "read_only": 1,
            },
            {
                "label": "Request for Material",
                "fieldname": "custom_request_for_material",
                "insert_after": "custom_request_for_purchase",
                "fieldtype": "Link",
                "options": "Request for Material",
                "read_only": 1,
            },
            {
                "label": "Customer",
                "fieldname": "custom_customer",
                "insert_after": "dimension_col_break",
                "fieldtype": "Link",
                "options": "Customer",
                "read_only": 1,
            },
            {
                "label": "Site",
                "fieldname": "custom_site",
                "insert_after": "custom_customer",
                "fieldtype": "Link",
                "options": "Operations Site",
                "read_only": 1,
            },
            {
                "label": "Refundable",
                "fieldname": "custom_refundable",
                "insert_after": "custom_site",
                "fieldtype": "Check",
                "read_only": 1,
            },
            {
                "label": "Margin Type",
                "fieldname": "custom_margin_type",
                "insert_after": "custom_refundable",
                "fieldtype": "Select",
                "options": "\nPercentage\nAmount",
                "read_only": 1,
            },
            {
                "label": "Margin Rate or Amount",
                "fieldname": "custom_margin_rate_or_amount",
                "insert_after": "custom_margin_type",
                "fieldtype": "Float",
                "read_only": 1,
            },
            {
                "label": "Purpose",
                "fieldname": "custom_purpose",
                "insert_after": "return_against",
                "fieldtype": "Select",
                "options": "\nPurchase\nSample Purchase",
                "read_only": 1
            },
        ]
    }
