def get_sales_invoice_item_custom_fields():
    return {
        "Sales Invoice Item": [
            {
                "fieldname": "column_break_13",
                "fieldtype": "Column Break",
                "insert_after": "brand"
            },
            {
                "fieldname": "site",
                "fieldtype": "Link",
                "insert_after": "column_break_13",
                "label": "Site",
                "options": "Operations Site"
            },
            {
                "fieldname": "days",
                "fieldtype": "Int",
                "insert_after": "site",
                "label": "Days"
            },
            {
                "fieldname": "basic_hours",
                "fieldtype": "Float",
                "insert_after": "days",
                "label": "Basic Hours"
            },
            {
                "fieldname": "total_hours",
                "fieldtype": "Float",
                "insert_after": "basic_hours",
                "label": "Total Hours"
            },
            {
                "fieldname": "hours_worked",
                "fieldtype": "Float",
                "insert_after": "total_hours",
                "label": "Total Hours Worked"
            },
            {
                "fieldname": "monthly_rate",
                "fieldtype": "Currency",
                "insert_after": "hours_worked",
                "label": "Monthly Rate",
                "options": "currency"
            },
            {
                "fieldname": "daily_rate",
                "fieldtype": "Currency",
                "insert_after": "monthly_rate",
                "label": "Daily Rate",
                "options": "currency"
            },
            {
                "fieldname": "hourly_rate",
                "fieldtype": "Currency",
                "insert_after": "daily_rate",
                "label": "Hourly Rate",
                "options": "currency"
            },
            {
                "fieldname": "inputted_qty",
                "fieldtype": "Float",
                "insert_after": "hourly_rate",
                "label": "Inputted Qty",
                "depends_on": "eval:parent.customer==='Incheon Kuwait Airport Services'"
            },
            {
                "fieldname": "category",
                "fieldtype": "Select",
                "insert_after": "inputted_qty",
                "label": "Category",
                "options": "\nSecurity\nOperation\nLeave\nIndemnity\nVisa and Residency\nSalary\nManagement Fee\nSettlement Support\nAdmin Manpower\nPurchase Order\nMonthly",
                "translatable": 1,
                "depends_on": "eval:parent.customer==='Incheon Kuwait Airport Services'"
            },
            {
                "fieldname": "gender",
                "fieldtype": "Link",
                "insert_after": "category",
                "label": "Gender",
                "options": "Gender",
                "read_only": 1
            },
            {
                "fieldname": "contracts_uom",
                "fieldtype": "Link",
                "insert_after": "gender",
                "label": "Contracts UOM",
                "options": "UOM",
                "read_only": 1
            },
            {
                "fieldname": "journal_entry",
                "fieldtype": "Link",
                "insert_after": "so_detail",
                "label": "Journal Entry",
                "options": "Journal Entry",
                "print_hide": 1,
                "read_only": 1
            },
            {
                "fieldname": "je_detail",
                "fieldtype": "Data",
                "insert_after": "journal_entry",
                "label": "Journal Entry Item",
                "print_hide": 1,
                "read_only": 1
            },
            {
                "fieldname": "custom_purchase_invoice",
                "fieldtype": "Link",
                "insert_after": "delivered_qty",
                "label": "Purchase Invoice",
                "options": "Purchase Invoice",
                "read_only": 1
            },
            {
                "fieldname": "custom_purchase_invoice_item",
                "fieldtype": "Link",
                "insert_after": "custom_purchase_invoice",
                "label": "Purchase Invoice Item",
                "options": "Purchase Invoice Item",
                "read_only": 1
            },
            {
                "fieldname": "custom_refundable",
                "fieldtype": "Check",
                "insert_after": "rate_with_margin",
                "label": "Refundable",
            },
            {
                "fieldname": "custom_contract_item_category",
                "fieldtype": "Link",
                "options": "Item Group",
                "insert_after": "customer_item_code",
                "label": "Contract Item Category",
                "allow_on_submit": 1,
                "fetch_from": "item_code.subitem_group",
                "fetch_if_empty": 1
            }



        ]
    }