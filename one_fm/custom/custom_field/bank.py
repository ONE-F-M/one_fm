def get_bank_custom_fields():
    return {
        "Bank": [
            {
                "fieldname": "data_export_configuration",
                "fieldtype": "Section Break",
                "insert_after": "plaid_access_token",
                "label": "Data Export Configuration"
            },
            {
                "fieldname": "payroll_export_template",
                "fieldtype": "Attach",
                "insert_after": "data_export_configuration",
                "label": "Payroll Export Template"
            },
            {
                "fieldname": "bank_code",
                "fieldtype": "Data",
                "insert_after": "bank_name",
                "label": "Bank Code",
                "reqd": 1
            }
        ]
    }
