def get_purchase_invoice_custom_fields():
    return {
        "Purchase Invoice": [
            {
                "fieldname": "employee_advance",
                "label": "Employee Advance",
                "fieldtype": "Link",
                "insert_after": "set_posting_time",
                "options": "Employee Advance",
                "read_only": 1
            },
            {
                "fieldname": "custom_customer",
                "label": "Customer",
                "fieldtype": "Link",
                "insert_after": "dimension_col_break",
                "options": "Customer",
                "read_only": 1
            },
            {
                "fieldname": "custom_site",
                "fieldtype": "Link",
                "insert_after": "project",
                "label": "Site",
                "options": "Operations Site",
                "read_only": 1
            },
            {
                "fieldname": "custom_refundable",
                "fieldtype": "Check",
                "insert_after": "custom_site",
                "label": "Refundable",
                "read_only": 1
            },
            {
                "fieldname": "custom_margin_type",
                "fieldtype": "Select",
                "insert_after": "custom_refundable",
                "label": "Margin Type",
                "translatable": 1,
                "options": "\nPercentage\nAmount"
            },
            {
                "fieldname": "custom_margin_rate_or_amount",
                "fieldtype": "Float",
                "insert_after": "custom_margin_type",
                "label": "Margin Rate or Amount",
            },
            {
                "fieldname": "custom_sales_invoice",
                "fieldtype": "Link",
                "insert_after": "remarks",
                "label": "Sales Invoice",
                "options": "Sales Invoice",
                "read_only": 1,
                "hidden": 1
            },
            {
                "label": "Purpose",
                "fieldname": "custom_purpose",
                "insert_after": "due_date",
                "fieldtype": "Select",
                "options": "\nPurchase\nSample Purchase",
                "read_only": 1
            },
        ]
    }
