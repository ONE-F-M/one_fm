def get_journal_entry_account_custom_fields():
    return {
        "Journal Entry Account": [
            {
                "fieldname": "include_amount_in_sales_invoice",
                "fieldtype": "Check",
                "insert_after": "account",
                "label": "Include Amount In Sales Invoice"
            },
            {
                "fieldname": "site",
                "fieldtype": "Link",
                "insert_after": "project",
                "label": "Site",
                "options": "Operations Site",
                "depends_on": "project"
            },
            {
                "fieldname": "employee",
                "fieldtype": "Link",
                "insert_after": "against_account",
                "label": "Employee",
                "options": "Employee",
                "depends_on": "eval:in_list([\"Leave\", \"Indemnity\"], doc.journal_entry_for)"
            },
            {
                "fieldname": "employee_name",
                "fieldtype": "Data",
                "insert_after": "purchase_request_ref",
                "label": "Employee Name",
                "fetch_from": "employee.employee_name",
                "read_only": 1
            },
            {
                "fieldname": "employee_id",
                "fieldtype": "Data",
                "insert_after": "employee",
                "label": "Employee Id",
                "fetch_from": "employee.employee_id",
                "read_only": 1,
                "translatable": 1
            },
            {
                "fieldname": "journal_entry_for",
                "fieldtype": "Select",
                "insert_after": "site",
                "label": "Journal Entry For",
                "options": "\nLeave\nIndemnity\nVisa and Residency",
                "depends_on": "eval:doc.project && in_list(doc.project,['Incheon Korea Airport'])",
                "translatable": 1
            },
            {
                "fieldname": "item_code",
                "fieldtype": "Link",
                "insert_after": "employee_name",
                "label": "Item Code",
                "options": "Item",
                "depends_on": "eval: doc.project != null && doc.include_amount_in_sales_invoice == 1"
            },
            {
                "fieldname": "purchase_request_ref",
                "fieldtype": "Data",
                "insert_after": "journal_entry_for",
                "label": "Purchase Request Ref",
                "depends_on": "eval:doc.journal_entry_for=='Visa and Residency'",
                "ignore_user_permissions": 1
            }
        ]
    }
