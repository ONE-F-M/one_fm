def get_depreciation_schedule_properties():
    return [
        {
            "doctype": "Property Setter",
            "doc_type": "Depreciation Schedule",
            "doctype_or_field": "DocField",
            "field_name": "make_depreciation_entry",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        }
    ]
