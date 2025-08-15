def get_asset_finance_book_properties():
    return [
        {
            "doctype_or_field": "DocField",
            "doc_type": "Asset Finance Book",
            "field_name": "expected_value_after_useful_life",
            "property": "depends_on",
            "property_type": "Data",
            "value": "eval:parent.doctype == 'Asset' || parent.doctype == 'Customer Asset'"
        }
    ]
