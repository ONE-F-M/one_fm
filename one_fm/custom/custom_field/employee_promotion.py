def get_employee_promotion_custom_fields():
	return {
		"Employee Promotion": [
			{
				"fieldname": "workflow_state",
				"label": "Workflow State",
				"fieldtype": "Link",
				"options": "Workflow State",
				"read_only": 1,
			},
		],
	}
