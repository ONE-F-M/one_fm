def get_supplier_group_custom_fields():
    return {
		"Supplier Group": [
			{
				"fieldname": "abbr",
				"fieldtype": "Data",
				"label": "Abbreviation",
				"insert_after": "supplier_group_name",
			},
			{
				"fieldname": "supplier_naming_series",
				"fieldtype": "Data",
                "hidden": 1,
				"insert_after": "abbr",
                "label": "Supplier Naming Series",
			}
		]
	}
