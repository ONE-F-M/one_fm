def get_wiki_page_custom_fields():
    return {
            "Wiki Page": [
            {
                "fieldname": "last_indexed_on",
                "fieldtype": "Datetime",
                "label": "Last Indexed On",
                "read_only": 1,
                "no_copy": 1,
                "insert_after": "language"
            }
        ]
    }
