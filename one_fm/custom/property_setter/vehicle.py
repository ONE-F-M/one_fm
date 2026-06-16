def get_vehicle_properties():
    return [
        {
            "doc_type": "Vehicle",
            "doctype_or_field": "DocType",
            "property": "image_field",
            "property_type": "Data",
            "value": "image"
        },
        {
            "doc_type": "Vehicle",
            "doctype_or_field": "DocType",
            "property": "quick_entry",
            "property_type": "Check",
            "value": "0"
        },
        {
            "doc_type": "Vehicle",
            "doctype_or_field": "DocField",
            "field_name": "employee",
            "property": "reqd",
            "value": "1",
            "property_type": "Check",
        },
        {
            "doc_type": "Vehicle",
            "doctype_or_field": "DocField",
            "field_name": "employee",
            "property": "fieldtype",
            "value": "Link",
            "property_type": "Select",
        },
        {
            "doc_type": "Vehicle",
            "doctype_or_field": "DocField",
            "field_name": "employee",
            "property": "options",
            "value": "Employee",
            "property_type": "Small Text",
        },
        {
            "doc_type": "Vehicle",
            "doctype_or_field": "DocField",
            "field_name": "location",
            "property": "label",
            "value": "Vehicle Location",
            "property_type": "Data",
        },
        {
            "doc_type": "Vehicle",
            "doctype_or_field": "DocField",
            "field_name": "location",
            "property": "fieldtype",
            "value": "Link",
            "property_type": "Select",
        },
        {
            "doc_type": "Vehicle",
            "doctype_or_field": "DocField",
            "field_name": "location",
            "property": "options",
            "value": "Location",
            "property_type": "Small Text",
        },
        {
            "doc_type": "Vehicle",
            "doctype_or_field": "DocField",
            "field_name": "location",
            "property": "reqd",
            "value": "1",
            "property_type": "Check",
        },
    ]