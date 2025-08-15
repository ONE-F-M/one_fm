def get_help_category_custom_fields():
    return {
        "Help Category": [
            {
                "fieldname": "column_break_5",
                "fieldtype": "Column Break",
                "insert_after": "route"
            },
            {
                "fieldname": "is_subcategory",
                "fieldtype": "Check",
                "insert_after": "column_break_5",
                "label": "Is Subcategory",
                "mandatory_depends_on": ""
            },
            {
                "fieldname": "category",
                "fieldtype": "Link",
                "insert_after": "is_subcategory",
                "label": "Category",
                "options": "Help Category",
                "depends_on": "eval:doc.is_subcategory",
                "mandatory_depends_on": "eval:doc.is_subcategory"
            }
        ]
    }
