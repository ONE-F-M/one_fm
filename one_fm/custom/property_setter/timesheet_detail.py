def get_timesheet_detail_properties():
    return [
        {
            "doc_type": "Timesheet Detail",
            "doctype_or_field": "DocField",
            "field_name": "billing_amount",
            "property": "precision",
            "property_type": "Select",
            "value": "3"
        },
        {
            "doc_type": "Timesheet Detail",
            "doctype_or_field": "DocField",
            "field_name": "billing_rate",
            "property": "precision",
            "property_type": "Select",
            "value": "3"
        }
    ]