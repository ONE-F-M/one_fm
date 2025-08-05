def get_sales_invoice_timesheet_properties():
    return [
        {
            "doctype": "Property Setter",
            "doc_type": "Sales Invoice Timesheet",
            "doctype_or_field": "DocField",
            "field_name": "timesheet_detail",
            "property": "hidden",
            "property_type": "Check",
            "value": "0"
        }
    ]