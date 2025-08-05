def get_purchase_receipt_item_properties():
    return [
        {
            "property": "hidden",
            "property_type": "Check",
            "value": "1",
            "doc_type": "Purchase Receipt Item",
            "doctype_or_field": "DocField",
            "field_name": "barcode"
        }
    ]
