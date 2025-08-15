def get_bank_account_custom_fields():
    return {
        "Bank Account": [
            {
                "fieldname": "iban_certificate",
                "fieldtype": "Attach",
                "insert_after": "iban",
                "label": "IBAN Certificate"
            },
            {
                "fieldname": "new_account",
                "fieldtype": "Check",
                "insert_after": "company",
                "label": "New Account"
            },
            {
                "fieldname": "attach_bank_form",
                "fieldtype": "Attach",
                "insert_after": "new_account",
                "label": "Attach Bank Form",
                "depends_on": "new_account"
            },
            {
                "fieldname": "onboard_employee",
                "fieldtype": "Link",
                "insert_after": "attach_bank_form",
                "label": "Onboard Employee",
                "options": "Onboard Employee"
            }
        ]
    }
