def get_purchase_receipt_properties():
    return [
        {
            "property": "default",
            "property_type": "Text",
            "value": "PRC-.YYYY.-.######",
            "doc_type": "Purchase Receipt",
            "doctype_or_field": "DocField",
            "field_name": "naming_series"
        },
        {
            "property": "options",
            "property_type": "Text",
            "value": "MAT-PRE-.YYYY.-\nPRC-.YYYY.-.######",
            "doc_type": "Purchase Receipt",
            "doctype_or_field": "DocField",
            "field_name": "naming_series"
        },
        {
            "property": "hidden",
            "property_type": "Check",
            "value": "1",
            "doc_type": "Purchase Receipt",
            "doctype_or_field": "DocField",
            "field_name": "scan_barcode"
        },
        {
            "property": "print_hide",
            "property_type": "Check",
            "value": "0",
            "doc_type": "Purchase Receipt",
            "doctype_or_field": "DocField",
            "field_name": "in_words"
        },
        {
            "property": "hidden",
            "property_type": "Check",
            "value": "0",
            "doc_type": "Purchase Receipt",
            "doctype_or_field": "DocField",
            "field_name": "in_words"
        }
    ]
