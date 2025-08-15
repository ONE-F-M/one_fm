def get_sales_invoice_timesheet_custom_fields():
    return {
        "Sales Invoice Timesheet": [
            {
                "fieldname": "item",
                "fieldtype": "Link",
                "insert_after": "timesheet_detail",
                "label": "Item",
                "options": "Item"
            }
        ]
    }