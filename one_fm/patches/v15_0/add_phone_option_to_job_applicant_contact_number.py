from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
	"""Add Phone validation option to Job Applicant contact_number field"""
	custom_fields = {
		"Job Applicant": [
			{
				"fieldname": "one_fm_contact_number",
				"fieldtype": "Data",
				"label": "Contact Number",
				"options": "Phone",
				"translatable": 1
			},
		]
	}
	# Use update=True to ensure the options are applied to the existing field
	create_custom_fields(custom_fields, update=True)
