def get_asset_repair_custom_fields():
	return {
		"Asset Repair": [
			{
				"fieldname": "custom_serial_no",
				"fieldtype": "Data",
				"label": "Serial No",
				"insert_after": "company",
				"fetch_from": "asset.custom_serial_no",
				"read_only": 1,
				"translatable": 1
			},
			{
				"fieldname": "custom_asset_location",
				"fieldtype": "Link",
				"label": "Asset Location",
				"insert_after": "custom_serial_no",
				"options": "Location",
				"fetch_from": "asset.location",
				"read_only": 1
			},
			{
				"fieldname": "custom_vendor_job_order_number",
				"fieldtype": "Data",
				"label": "Vendor Job Order Number",
				"insert_after": "purchase_invoice",
				"translatable": 1
			}
		]
	}
