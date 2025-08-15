def get_sales_invoice_custom_fields():
    return {
        "Sales Invoice": [
            {
                "fieldname": "custom_client_confirmation_copy",
                "fieldtype": "Attach",
                "insert_after": "terms",
                "label": "Client Confirmation Copy"
            },
            {
                "fieldname": "loan",
                "fieldtype": "Link",
                "insert_after": "customer",
                "label": "Loan",
                "options": "Loan",
                "print_hide": 1,
                "translatable": 1
            },
            {
                "fieldname": "settlement_amount",
                "fieldtype": "Currency",
                "insert_after": "balance_in_advance_account",
                "label": "Settlement Amount",
                "depends_on": "eval:doc.automatic_settlement==\"Yes\"",
                "description": "Amount from the customer advances that will be used to settle this invoice."
            },
            {
                "fieldname": "automatic_settlement",
                "fieldtype": "Select",
                "insert_after": "update_billed_amount_in_sales_order",
                "label": "Settle From Unearned Revenue",
                "options": "\nYes\nNo"
            },
            {
                "fieldname": "balance_in_advance_account",
                "fieldtype": "Currency",
                "insert_after": "contracts",
                "label": "Balance In Advance Account",
                "read_only": 1
            },
            {
                "fieldname": "contracts",
                "fieldtype": "Link",
                "insert_after": "customer_name",
                "label": "Contracts",
                "options": "Contracts",
                "depends_on": "eval:doc.customer"
            },
            {
                "fieldname": "add_social_security",
                "fieldtype": "Button",
                "insert_after": "social_security_items",
                "label": "Add To Item Table"
            },
            {
                "fieldname": "social_security_item",
                "fieldtype": "Link",
                "insert_after": "section_break_53",
                "label": "Social Security Item",
                "options": "Item"
            },
            {
                "fieldname": "social_security_items",
                "fieldtype": "Table",
                "insert_after": "social_security_item",
                "label": "Social Security Items",
                "options": "Social Security"
            },
            {
                "fieldname": "section_break_53",
                "fieldtype": "Section Break",
                "insert_after": "ignore_pricing_rule",
                "depends_on": "eval:doc.customer==\"Incheon Kuwait Airport Services\""
            },
            {
                "fieldname": "po",
                "fieldtype": "Attach",
                "insert_after": "po_date",
                "label": "Customer's Purchase Order"
            },
            {
                "fieldname": "format",
                "fieldtype": "Link",
                "insert_after": "language",
                "label": "Print Format",
                "options": "Print Format",
                "allow_on_submit": 1
            }
        ]
    }
