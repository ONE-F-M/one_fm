def get_payroll_employee_detail_custom_fields():
    return {
        "Payroll Employee Detail": [
            {
                "fieldname": "salary_slip_details",
                "fieldtype": "Section Break",
                "insert_after": "mosal_id",
                "label": "Salary Slip Details"
            },
            {
                "fieldname": "justification_needed_on_deduction",
                "fieldtype": "Check",
                "insert_after": "salary_slip_details",
                "label": "Justification Needed on Deduction",
                "read_only": 1
            },
            {
                "fieldname": "iban_number",
                "fieldtype": "Data",
                "insert_after": "bank_details",
                "label": "IBAN Number"
            },
            {
                "fieldname": "civil_id_number",
                "fieldtype": "Data",
                "insert_after": "salary_mode",
                "label": "Civil ID Number",
                "fetch_from": "employee.one_fm_civil_id",
                "translatable": 1
            },
            {
                "fieldname": "payment_amount",
                "fieldtype": "Currency",
                "insert_after": "iban_number",
                "label": "Payment Amount"
            },
            {
                "fieldname": "bank_code",
                "fieldtype": "Data",
                "insert_after": "payment_amount",
                "label": "Bank Code"
            },
            {
                "fieldname": "mosal_id",
                "fieldtype": "Data",
                "insert_after": "civil_id_number",
                "label": "MOSAL ID",
                "fetch_from": "employee.pam_file_number",
                "translatable": 1
            },
            {
                "fieldname": "bank_details",
                "fieldtype": "Section Break",
                "insert_after": "designation",
                "label": "Bank Details"
            },
            {
                "fieldname": "column_break_9",
                "fieldtype": "Column Break",
                "insert_after": "bank_code"
            },
            {
                "fieldname": "salary_mode",
                "fieldtype": "Select",
                "insert_after": "column_break_9",
                "label": "Salary Mode",
                "options": "\nBank\nCash\nCheque",
                "translatable": 1
            }
        ]
    }
