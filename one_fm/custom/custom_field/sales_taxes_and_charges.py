def get_sales_taxes_and_charges_custom_fields():
    return {
        "Sales Taxes and Charges": [
            {
                "fieldname": "custom_add_or_deduct",
                "fieldtype": "Select",
                "label": "Add or Deduct",
                "insert_after": "row_id",
                "options": "Add\nDeduct",
                "reqd": 1,
                "default": "Deduct",
                "in_list_view": 0,
            }
        ]
    }
