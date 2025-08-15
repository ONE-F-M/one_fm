def get_asset_custom_fields():
    return {
        "Asset": [
            {
                "fieldname": "project",
                "fieldtype": "Link",
                "label": "Project",
                "hidden": 1,
                "allow_on_submit": 1,
                "insert_after": "dimension_col_break",
                "options": "Project"
            },
            {
                "fieldname": "transfer_from_warehouse",
                "fieldtype": "Section Break",
                "label": "Transfer from warehouse",
                "insert_after": "number_of_depreciations_booked"
            },
            {
                "fieldname": "asset_transfer",
                "fieldtype": "Table",
                "label": "Asset Transfer",
                "insert_after": "transfer_from_warehouse",
                "options": "Asset Transfer Detail"
            }
        ]
    }
