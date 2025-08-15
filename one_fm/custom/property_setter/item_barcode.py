def get_item_barcode_properties():
    return [
        {
            "doctype_or_field": "DocField",
            "doc_type": "Item Barcode",
            "field_name": "barcode",
            "property": "hidden",
            "property_type": "Check",
            "value": 0
        },
        {
            "doctype_or_field": "DocField",
            "doc_type": "Item Barcode",
            "field_name": "item",
            "property": "read_only",
            "property_type": "Check",
            "value": 1
        }
    ]
