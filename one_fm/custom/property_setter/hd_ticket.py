def get_hd_ticket_properties():
    return [
        {
            "doctype_or_field":"DocField",
            "doc_type":"HD Ticket",
            "field_name":"status",
            "property":"options",
            "value":"Draft\nOpen\nReplied\nOn Hold\nPending Deployment\nResolved\nClosed",
            "default_value":"Open"
        },
        {
            "doctype_or_field":"DocField",
            "doc_type":"HD Ticket",
            "field_name":"agent_group",
            "property":"hidden",
            "value":"1"
        }
    ]
