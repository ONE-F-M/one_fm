def get_asset_category_account_custom_fields():
    return {
        "Asset Category Account": [
            {
                "fieldname": "direct_depreciation_expense_account",
                "fieldtype": "Link",
                "insert_after": "depreciation_expense_account",
                "label": "Direct Depreciation Expense Account",
                "options": "Account"
            },
            {
                "fieldname": "indirect_depreciation_expense_account",
                "fieldtype": "Link",
                "insert_after": "direct_depreciation_expense_account",
                "label": "Indirect Depreciation Expense Account",
                "options": "Account",
                "in_list_view": 1
            }
        ]
    }
