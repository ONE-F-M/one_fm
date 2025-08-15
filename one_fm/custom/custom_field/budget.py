def get_budget_custom_fields():
    return {
        "Budget": [
            {
                "fieldname": "column_break_21",
                "fieldtype": "Column Break",
                "insert_after": "action_if_accumulated_monthly_budget_exceeded"
            },
            {
                "fieldname": "applicable_on_stock_entry",
                "fieldtype": "Check",
                "insert_after": "column_break_21",
                "label": "Applicable on Stock Entry"
            },
            {
                "fieldname": "action_if_annual_budget_exceeded_on_se",
                "fieldtype": "Select",
                "insert_after": "applicable_on_stock_entry",
                "label": "Action if Annual Budget Exceeded on SE",
                "options": "\nStop\nWarn\nIgnore",
                "depends_on": "applicable_on_stock_entry"
            },
            {
                "fieldname": "action_if_accumulated_monthly_budget_exceeded_on_se",
                "fieldtype": "Select",
                "insert_after": "action_if_annual_budget_exceeded_on_se",
                "label": "Action if Accumulated Monthly Budget Exceeded on SE",
                "options": "\nStop\nWarn\nIgnore",
                "depends_on": "applicable_on_stock_entry"
            }
        ]
    }
