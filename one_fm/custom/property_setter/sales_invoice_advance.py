def get_sales_invoice_advance_properties():
	return [
		{
			"doctype": "Property Setter",
			"doc_type": "Sales Invoice Advance",
			"doctype_or_field": "DocField",
			"field_name": "advance_amount",
			"property": "label",
			"property_type": "Data",
			"value": "Available Advance amount"
		},
		{
			"doctype": "Property Setter",
			"doc_type": "Sales Invoice Advance",
			"doctype_or_field": "DocType",
			"property": "field_order",
			"property_type": "Data",
			"value": '["reference_type", "reference_name", "remarks", "reference_row", "col_break1", "custom_received_amount", "advance_amount", "allocated_amount", "exchange_gain_loss", "ref_exchange_rate"]'
		}
	]