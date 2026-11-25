def get_request_for_material_custom_fields():
	return {
		"Request for Material": [
			{
				"fieldname": "workflow_state",
				"label": "Workflow State",
				"fieldtype": "Link",
				"options": "Workflow State",
				"hidden": 1,
				"no_copy": 1,
				"allow_on_submit": 1,
			}
		]
	}
