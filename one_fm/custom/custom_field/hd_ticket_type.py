def get_hd_ticket_type_custom_fields():
	"""Return a dictionary of custom fields for the HD Ticket Type document."""
	return {
		"HD Ticket Type": [
			{
				"fieldname": "initiate_process_change_request",
				"fieldtype": "Check",
				"label": "Initiate Process Change Request",
				"insert_after": "priority",
				"description": "If checked, HD Tickets of this type can be converted to Process Change Requests.",
			},
		]
	}
