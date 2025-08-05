def get_price_list_custom_fields():
    return {
        "Price List": [
            {
                "fieldname": "project",
                "fieldtype": "Link",
                "insert_after": "price_list_name",
                "label": "Project",
                "options": "Project"
            }
        ]
    }
