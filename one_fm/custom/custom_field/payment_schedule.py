def get_payment_schedule_custom_fields():
    return {
        "Payment Schedule": [
            {
                "fieldname": "credit_days",
                "fieldtype": "Int",
                "insert_after": "due_date",
                "label": "Credit Days",
                "bold": 1
            },
            {
                "fieldname": "one_fm_payment",
                "fieldtype": "Select",
                "insert_after": "mode_of_payment",
                "label": "Payment",
                "fetch_from": "payment_term.one_fm_payment",
                "options": "\nIn Advance\nOn Delivery",
                "translatable": 1
            }
        ]
    }
