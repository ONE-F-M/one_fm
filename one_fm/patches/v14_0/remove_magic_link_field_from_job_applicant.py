import frappe

def execute():
	fields = ['magic_link']
	for field in fields:
		field_name = 'Job Applicant-'+field
		if frappe.db.exists('Custom Field', {'name': field_name}):
			frappe.delete_doc('Custom Field', field_name)
