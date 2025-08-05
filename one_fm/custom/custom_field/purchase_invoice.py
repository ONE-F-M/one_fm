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
            }
        ]
    }
