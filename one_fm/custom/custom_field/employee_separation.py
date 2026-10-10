def get_employee_separation_custom_fields():
	return {
		"Employee Separation": [
			{
				"fieldname": "mode_of_separation",
				"label": "Mode of Separation",
				"fieldtype": "Select",
				"options": "Resignation\nTermination",
				"reqd": 1,
			},
			{
				"fieldname": "relieving_date",
				"label": "Relieving Date",
				"fieldtype": "Data",
			},
			{
				"fieldname": "type_of_exit",
				"label": "Type of Exit",
				"fieldtype": "Data",
			},
			{
				"fieldname": "workflow_state",
				"label": "Workflow State",
				"fieldtype": "Link",
				"options": "Workflow State",
				"insert_after": "type_of_exit",
				"hidden": 1,
				"allow_on_submit": 1,
				"no_copy": 1,
			},
		],
	}
