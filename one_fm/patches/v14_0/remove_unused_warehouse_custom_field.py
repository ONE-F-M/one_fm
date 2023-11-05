import frappe

def execute():
	fields = ['ownership', 'column_break_14', 'section_break_12', 'column_break_21', 'column_break_uv3ut']
	for field in fields:
		field_name = 'Warehouse-'+field
		if frappe.db.exists('Custom Field', {'name': field_name}):
			frappe.delete_doc('Custom Field', field_name)
