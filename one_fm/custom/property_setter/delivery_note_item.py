def get_delivery_note_item_properties():
    return [
        {
            "doctype": "Property Setter",
            "doc_type": "Delivery Note Item",
            "doctype_or_field": "DocField",
            "field_name": "serial_no",
            "property": "in_list_view",
            "property_type": "Check",
            "value": "1"
        }
    ]
