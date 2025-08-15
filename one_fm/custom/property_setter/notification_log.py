def get_notification_log_properties():
    return [
        {
            "doc_type": "Notification Log",
            "doctype_or_field": "DocField",
            "field_name": "open_reference_document",
            "property": "depends_on",
            "property_type": "Data",
            "value": "eval:doc.check_baled"
        }
    ]
