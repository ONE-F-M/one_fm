def get_location_properties():
    return [
        {
            "doc_type": "Location",
            "doctype_or_field": "DocField",
            "field_name": "longitude",
            "property": "precision",
            "property_type": "Select",
            "value": "9"
        },
        {
            "doc_type": "Location",
            "doctype_or_field": "DocField",
            "field_name": "latitude",
            "property": "precision",
            "property_type": "Select",
            "value": "9"
        },
        {
            "doc_type": "Location",
            "doctype_or_field": "DocField",
            "field_name": "longitude",
            "property": "reqd",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Location",
            "doctype_or_field": "DocField",
            "field_name": "latitude",
            "property": "reqd",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Location",
            "doctype_or_field": "DocField",
            "field_name": "area_uom",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Location",
            "doctype_or_field": "DocField",
            "field_name": "area",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Location",
            "doctype_or_field": "DocField",
            "field_name": "is_group",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Location",
            "doctype_or_field": "DocField",
            "field_name": "is_container",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Location",
            "doctype_or_field": "DocField",
            "field_name": "parent_location",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doc_type": "Location",
            "doctype_or_field": "DocField",
            "field_name": "location",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        }
    ]
