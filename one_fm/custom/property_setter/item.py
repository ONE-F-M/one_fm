def get_item_properties():
    return [
        {
            "doctype_or_field": "DocField",
            "doc_type": "Item",
            "field_name": "item_name",
            "property": "read_only",
            "property_type": "Check",
            "value": 1
        },
        {
            "doctype_or_field": "DocField",
            "doc_type": "Item",
            "field_name": "description",
            "property": "hidden",
            "property_type": "Check",
            "value": 0
        }
    ]
