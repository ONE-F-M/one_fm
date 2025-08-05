def get_stock_entry_detail_properties():
    return [
        {
            "doc_type": "Stock Entry Detail",
            "doctype_or_field": "DocField",
            "field_name": "basic_rate",
            "property": "read_only",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Stock Entry Detail",
            "doctype_or_field": "DocField",
            "field_name": "uom",
            "property": "read_only",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Stock Entry Detail",
            "doctype_or_field": "DocField",
            "field_name": "description",
            "property": "read_only",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Stock Entry Detail",
            "doctype_or_field": "DocField",
            "field_name": "t_warehouse",
            "property": "ignore_user_permissions",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Stock Entry Detail",
            "doctype_or_field": "DocField",
            "field_name": "s_warehouse",
            "property": "ignore_user_permissions",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Stock Entry Detail",
            "doctype_or_field": "DocField",
            "field_name": "barcode",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        }
    ]