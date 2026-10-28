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
            },
            {
                "fieldname": "civil_id",
                "fieldtype": "Data",
                "insert_after": "party",
                "label": "Civil ID",
                # Client-side only in Frappe v15; enforced server-side by
                # one_fm.overrides.bank_account.validate_civil_id.
                "mandatory_depends_on": "eval:!doc.is_company_account && (!doc.party_type || doc.party_type == 'Employee')"
            }
        ]
    }
