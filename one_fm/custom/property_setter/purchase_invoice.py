def get_purchase_invoice_properties():
    return [
        {
            "property": "default",
            "property_type": "Text",
            "value": "PIN-.YYYY.-.######",
            "doc_type": "Purchase Invoice",
            "doctype_or_field": "DocField",
            "field_name": "naming_series"
        },
        {
            "property": "options",
            "property_type": "Text",
            "value": "ACC-PINV-.YYYY.-\nPIN-.YYYY.-.######",
            "doc_type": "Purchase Invoice",
            "doctype_or_field": "DocField",
            "field_name": "naming_series"
        },
        {
            "property": "hidden",
            "property_type": "Check",
            "value": "1",
            "doc_type": "Purchase Invoice",
            "doctype_or_field": "DocField",
            "field_name": "scan_barcode"
        },
        {
            "property": "print_hide",
            "property_type": "Check",
            "value": "0",
            "doc_type": "Purchase Invoice",
            "doctype_or_field": "DocField",
            "field_name": "in_words"
        },
        {
            "property": "hidden",
            "property_type": "Check",
            "value": "0",
            "doc_type": "Purchase Invoice",
            "doctype_or_field": "DocField",
            "field_name": "in_words"
        },
        {
            "property": "print_hide",
            "property_type": "Check",
            "value": "0",
            "doc_type": "Purchase Invoice",
            "doctype_or_field": "DocField",
            "field_name": "rounded_total"
        },
        {
            "property": "hidden",
            "property_type": "Check",
            "value": "0",
            "doc_type": "Purchase Invoice",
            "doctype_or_field": "DocField",
            "field_name": "rounded_total"
        },
        {
            "property": "print_hide",
            "property_type": "Check",
            "value": "1",
            "doc_type": "Purchase Invoice",
            "doctype_or_field": "DocField",
            "field_name": "base_rounded_total"
        },
        {
            "property": "hidden",
            "property_type": "Check",
            "value": "0",
            "doc_type": "Purchase Invoice",
            "doctype_or_field": "DocField",
            "field_name": "base_rounded_total"
        },
        {
            "property": "hidden",
            "property_type": "Check",
            "value": "1",
            "doc_type": "Purchase Invoice",
            "doctype_or_field": "DocField",
            "field_name": "cost_center"
        },
        {
            "property": "print_hide",
            "property_type": "Check",
            "value": "1",
            "doc_type": "Purchase Invoice",
            "doctype_or_field": "DocField",
            "field_name": "payment_schedule"
        },
        {
            "property": "print_hide",
            "property_type": "Check",
            "value": "0",
            "doc_type": "Purchase Invoice",
            "doctype_or_field": "DocField",
            "field_name": "due_date"
        }
    ]
