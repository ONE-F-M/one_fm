def get_expense_claim_detail_custom_fields():
    return {
        "Expense Claim Detail": [
            {
                "fieldname": "attatch_bill",
                "fieldtype": "Attach",
                "insert_after": "sanctioned_amount",
                "label": "attatch bill"
            }
        ]
    }
