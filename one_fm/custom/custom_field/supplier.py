def get_supplier_custom_fields():
    return {
        "Supplier": [
            {
                "fieldname": "supplier_payment_terms",
                "fieldtype": "Link",
                "label": "Supplier Payment Terms",
                "insert_after": "country",
                "options": "Mode of Payment"
            },
            {
                "fieldname": "status",
                "fieldtype": "Select",
                "label": "Status",
                "insert_after": "column_break0",
                "options": "Enable\nDisable\nBlacklist",
                "default": "Enable"
            },
            {
                "fieldname": "bank_account_info",
                "fieldtype": "Section Break",
                "label": "Bank Account Info",
                "insert_after": "prevent_pos"
            },
            {
                "fieldname": "iban",
                "fieldtype": "Data",
                "label": "IBAN",
                "insert_after": "bank_account_info",
                "translatable": 1
            },
            {
                "fieldname": "bank",
                "fieldtype": "Link",
                "label": "Bank",
                "insert_after": "iban",
                "options": "Bank",
                "depends_on": "eval:doc.location=='External'"
            },
            {
                "fieldname": "bank_account_no",
                "fieldtype": "Data",
                "label": "Bank Account No",
                "insert_after": "bank",
                "translatable": 1,
                "depends_on": "eval:doc.location=='External'"
            },
            {
                "fieldname": "swift_code",
                "fieldtype": "Data",
                "label": "SWIFT Code",
                "insert_after": "bank_account_no",
                "translatable": 1,
                "depends_on": "eval:doc.location=='External'"
            },
            {
                "fieldname": "column_break_31",
                "fieldtype": "Column Break",
                "insert_after": "swift_code"
            },
            {
                "fieldname": "location",
                "fieldtype": "Select",
                "label": "Location",
                "insert_after": "column_break_31",
                "options": "Internal\nExternal",
                "default": "Internal"
            },
            {
                "fieldname": "supplier_group_section",
                "fieldtype": "Section Break",
                "label": "Supplier Group Section",
                "insert_after": "location"
            },
            {
                "fieldname": "supplier_group_table",
                "fieldtype": "Table",
                "label": "Supplier Group Table",
                "insert_after": "supplier_group_section",
                "options": "Supplier Group Table"
            },
            {
                "fieldname": "supplier_document_section",
                "fieldtype": "Section Break",
                "label": "Supplier Document Section",
                "insert_after": "supplier_group_table"
            },
            {
                "fieldname": "supplier_group_abbr",
                "fieldtype": "Data",
                "label": "Supplier Group Abbreviation",
                "insert_after": "status",
                "fetch_from": "supplier_group.abbr",
                "hidden": 1,
                "read_only": 1
            },
            {
                "fieldname": "expense_account",
                "fieldtype": "Link",
                "label": "Expense Account",
                "insert_after": "supplier_payment_terms",
                "options": "Account"
            },
            {
                "fieldname": "supplier_name_in_arabic",
                "fieldtype": "Data",
                "label": "Supplier Name in Arabic",
                "insert_after": "supplier_name",
                "translatable": 1
            },
            {
                "fieldname": "custom_is_courier",
                "fieldtype": "Check",
                "label": "Is Courier",
                "insert_after": "is_transporter",
                "default": "0"
            },
            {
                "fieldname": "custom_api_settings",
                "fieldtype": "Section Break",
                "label": "API Settings",
                "insert_after": "custom_is_courier",
                "depends_on": "eval:doc.custom_is_courier"
            },
            {
                "fieldname": "custom_courier_api_provider",
                "fieldtype": "Select",
                "label": "Courier API Provider",
                "insert_after": "custom_api_settings",
                "options": "\nDHL\nFedEx\nUPS",
                "mandatory_depends_on": "eval:doc.custom_is_courier"
            },
            {
                "fieldname": "custom_column_break_courier",
                "fieldtype": "Column Break",
                "insert_after": "custom_courier_api_provider"
            },
            {
                "fieldname": "custom_api_key",
                "fieldtype": "Password",
                "label": "API Key",
                "insert_after": "custom_column_break_courier",
                "depends_on": "eval:doc.custom_courier_api_provider && doc.custom_courier_api_provider !== ''"
            },
            {
                "fieldname": "custom_api_secret",
                "fieldtype": "Password",
                "label": "API Secret",
                "insert_after": "custom_api_key",
                "depends_on": "eval:doc.custom_courier_api_provider && doc.custom_courier_api_provider !== ''"
            },
            {
                "fieldname": "custom_api_account_number",
                "fieldtype": "Data",
                "label": "API Account Number",
                "insert_after": "custom_api_secret",
                "depends_on": "eval:doc.custom_courier_api_provider && doc.custom_courier_api_provider !== ''"
            }
        ]
    }