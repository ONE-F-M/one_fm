def get_customer_custom_fields():
    return {
        "Customer": [
            {
                "fieldname": "attachments",
                "fieldtype": "Section Break",
                "insert_after": "represents_company",
                "label": "Attachments",
                "collapsible": 1
            },
            {
                "fieldname": "civil_id",
                "fieldtype": "Attach",
                "insert_after": "attachments",
                "label": "Civil ID",
                "depends_on": "eval:doc.customer_type==\"Individual\""
            },
            {
                "fieldname": "article_of_assosciation",
                "fieldtype": "Attach",
                "insert_after": "civil_id",
                "label": "Article of Assosciation",
                "depends_on": "eval:doc.customer_type==\"Company\""
            },
            {
                "fieldname": "license",
                "fieldtype": "Attach",
                "insert_after": "article_of_assosciation",
                "label": "Commercial License",
                "depends_on": "eval:doc.customer_type==\"Company\""
            },
            {
                "fieldname": "custom_paci",
                "fieldtype": "Attach",
                "insert_after": "license",
                "label": "PACI"
            },
            {
                "fieldname": "custom_pam",
                "fieldtype": "Attach",
                "insert_after": "custom_paci",
                "label": "PAM"
            },
            {
                "fieldname": "column_break_22",
                "fieldtype": "Column Break",
                "insert_after": "custom_pam"
            },
            {
                "fieldname": "authorized_signatory",
                "fieldtype": "Attach",
                "insert_after": "column_break_22",
                "label": "Authorized Signatory",
                "depends_on": "eval:doc.customer_type==\"Company\""
            },
            {
                "fieldname": "authorized_signatory_civil_id",
                "fieldtype": "Attach",
                "insert_after": "authorized_signatory",
                "label": "Authorized Signatory Civil ID",
                "depends_on": "eval:doc.customer_type==\"Company\""
            },
            {
                "fieldname": "custom_commercial_register",
                "fieldtype": "Attach",
                "insert_after": "authorized_signatory_civil_id",
                "label": "Commercial Register"
            },
            {
                "fieldname": "custom_certificate_of_no_financial_restriction",
                "fieldtype": "Attach",
                "insert_after": "custom_commercial_register",
                "label": "Certificate of No Financial Restriction"
            },
            {
                "fieldname": "custom_authorized_signature_from_coc",
                "fieldtype": "Attach",
                "insert_after": "custom_certificate_of_no_financial_restriction",
                "label": "Authorized Signature from CoC"
            },
            {
                "fieldname": "custom_column_break_bbn0d",
                "fieldtype": "Column Break",
                "insert_after": "custom_authorized_signature_from_coc"
            },
            {
                "fieldname": "custom_iban_certificate",
                "fieldtype": "Attach",
                "insert_after": "custom_column_break_bbn0d",
                "label": "IBAN Certificate"
            },
            {
                "fieldname": "custom_canceled_cheque",
                "fieldtype": "Attach",
                "insert_after": "custom_iban_certificate",
                "label": "Canceled Cheque"
            },
            {
                "fieldname": "custom_cash_payment",
                "fieldtype": "Attach",
                "insert_after": "custom_canceled_cheque",
                "label": "Cash Payment"
            },
            {
                "fieldname": "customer_name_in_arabic",
                "fieldtype": "Data",
                "insert_after": "customer_name",
                "label": "Full Name In Arabic",
                "translatable": 1,
                "reqd": 1
            },
            {
                "fieldname": "website_image",
                "fieldtype": "Attach Image",
                "insert_after": "image",
                "label": "Website Image",
                "hidden": 1
            }
        ]
    }
