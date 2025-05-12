from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
	create_custom_fields({
		"Designation": [
			{
				"fieldname": "disabled",
				"fieldtype": "Check",
				"label": "Disabled",
				"insert_after": "custom_job_offer_term_template",
				"description": "This field is used to disable a designation, ensuring it does not appear in the system when filtering or selecting designations."
			},
		]
	} )