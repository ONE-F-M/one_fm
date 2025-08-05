def get_stock_entry_properties():
    return [
        {
            "doc_type": "Stock Entry",
            "doctype_or_field": "DocField",
            "field_name": "project",
            "property": "read_only",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Stock Entry",
            "doctype_or_field": "DocField",
            "field_name": "project",
            "property": "fetch_if_empty",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Stock Entry",
            "doctype_or_field": "DocField",
            "field_name": "project",
            "property": "fetch_from",
            "property_type": "Small Text",
            "value": "from_warehouse.one_fm_project"
        },
        {
            "doc_type": "Stock Entry",
            "doctype_or_field": "DocField",
            "field_name": "to_warehouse",
            "property": "ignore_user_permissions",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Stock Entry",
            "doctype_or_field": "DocField",
            "field_name": "from_warehouse",
            "property": "ignore_user_permissions",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Stock Entry",
            "doctype_or_field": "DocField",
            "field_name": "naming_series",
            "property": "options",
            "property_type": "Text",
            "value": "MAT-STE-.YYYY.-"
        },
        {
            "doc_type": "Stock Entry",
            "doctype_or_field": "DocField",
            "field_name": "from_bom",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Stock Entry",
            "doctype_or_field": "DocField",
            "field_name": "printing_settings",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Stock Entry",
            "doctype_or_field": "DocField",
            "field_name": "get_stock_and_rate",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Stock Entry",
            "doctype_or_field": "DocField",
            "field_name": "inspection_required",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Stock Entry",
            "doctype_or_field": "DocField",
            "field_name": "set_posting_time",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Stock Entry",
            "doctype_or_field": "DocField",
            "field_name": "scan_barcode",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        }
    ]