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
                "label": "License",
                "depends_on": "eval:doc.customer_type==\"Company\""
            },
            {
                "fieldname": "column_break_22",
                "fieldtype": "Column Break",
                "insert_after": "license"
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
                "fieldname": "customer_name_in_arabic",
                "fieldtype": "Data",
                "insert_after": "customer_name",
                "label": "Full Name In Arabic",
                "translatable": 1
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
