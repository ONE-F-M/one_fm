import frappe

def execute():
	fields = ['one_fm_serial_no_and_batch_section', 'one_fm_serial_numbers', 'one_fm_serial_no_and_batch_cb', 'one_fm_batch_numbers']
	for field in fields:
		field_name = 'Purchase Receipt Item-'+field
		if frappe.db.exists('Custom Field', {'name': field_name}):
			frappe.delete_doc('Custom Field', field_name)
