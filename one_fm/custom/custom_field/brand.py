def get_brand_custom_fields():
    return {
        "Brand": [
            {
                "fieldname": "item_group",
                "fieldtype": "Link",
                "insert_after": "description",
                "label": "Item Group",
                "options": "Item Group"
            }
        ]
    }
