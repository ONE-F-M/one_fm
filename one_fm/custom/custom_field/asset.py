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
            },
            {
                "fieldname": "custom_is_refundable",
                "fieldtype": "Check",
                "label": "Is Refundable",
                "insert_after": "is_composite_asset"
            },
            {
                "fieldname": "custom_serial_and_warranty_details",
                "fieldtype": "Section Break",
                "label": "Serial and Warranty Details",
                "insert_after": "total_asset_cost",
            },
            {
                "fieldname": "custom_serial_no",
                "fieldtype": "Data",
                "label": "Serial No",
                "insert_after": "custom_serial_and_warranty_details",
                "translatable": 1,
            },
            {
                "fieldname": "custom_column_break_ffjzp",
                "fieldtype": "Column Break",
                "insert_after": "custom_serial_no",
            },
            {
                "fieldname": "custom_warranty_start_date",
                "fieldtype": "Date",
                "label": "Warranty Start Date",
                "insert_after": "custom_column_break_ffjzp",
            },
            {
                "fieldname": "custom_column_break_7darf",
                "fieldtype": "Column Break",
                "insert_after": "custom_warranty_start_date",
            },
            {
                "fieldname": "custom_warranty_end_date",
                "fieldtype": "Date",
                "label": "Warranty End Date",
                "insert_after": "custom_column_break_7darf",
            },
        ]
    }
