def get_payment_request_custom_fields():
    return {
        "Payment Request": [
            {
                "fieldname": "one_fm_manual_report",
                "fieldtype": "Attach",
                "insert_after": "grand_total",
                "label": "Manual Report",
                "depends_on": "eval: doc.reference_doctype == \"PIFSS Monthly Deduction\""
            }
        ]
    }
