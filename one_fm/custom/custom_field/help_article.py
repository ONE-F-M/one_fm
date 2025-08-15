def get_help_article_custom_fields():
    return {
        "Help Article": [
            {
                "fieldname": "subcategory",
                "fieldtype": "Link",
                "insert_after": "category",
                "label": "Sub Category",
                "options": "Help Category",
                "depends_on": "category",
                "mandatory_depends_on": "eval:doc.category"
            }
        ]
    }
