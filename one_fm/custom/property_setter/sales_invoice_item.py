def get_sales_invoice_item_properties():
    return [
        {
            "doctype": "Property Setter",
            "doc_type": "Sales Invoice Item",
            "doctype_or_field": "DocField",
            "field_name": "barcode",
            "property": "hidden",
            "property_type": "Check",
            "value": "0"
        }
    ]