from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
	create_custom_fields({
		"HR Settings": [
			{
				"fieldname": "annual_leave_threshold",
				"fieldtype": "Int",
				"label": "Annual Leave Threshold",
				"insert_after": "auto_leave_encashment",
				"default": 60,
				"description": "The minimum number of annual leave days an employee must accumulate before a leave acknowledgment form is automatically generated."
			},
		]
	} )
