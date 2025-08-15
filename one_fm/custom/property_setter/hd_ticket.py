def get_hd_ticket_properties():
    return [
        {
            "doctype_or_field": "DocField",
            "doc_type": "HD Ticket",
            "field_name": "custom_dev_ticket",
            "property": "read_only",
            "property_type": "Check",
            "value": 1
        },
        {
            "doctype_or_field": "DocField",
            "doc_type": "HD Ticket",
            "field_name": "custom_dev_ticket",
            "property": "translatable",
            "property_type": "Check",
            "value": 1
        }
    ]
