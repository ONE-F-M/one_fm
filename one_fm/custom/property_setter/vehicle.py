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
            "property": "mandatory_depends_on",
            "value": "eval:doc.one_fm_vehicle_category != 'Subcontractor'"
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
        # WI-001765: the list view identifies a vehicle by its registration plate,
        # not its odometer reading. Production has been configured this way by hand
        # since before the app tracked it; these two setters codify that so every
        # environment matches. The other columns production sets (fuel_type, model,
        # uom, vehicle_value) are already in_list_view by ERPNext default.
        {
            "doc_type": "Vehicle",
            "doctype_or_field": "DocField",
            "field_name": "license_plate",
            "property": "in_list_view",
            "value": "1",
            "property_type": "Check",
        },
        {
            "doc_type": "Vehicle",
            "doctype_or_field": "DocField",
            "field_name": "last_odometer",
            "property": "in_list_view",
            "value": "0",
            "property_type": "Check",
        },
    ]
