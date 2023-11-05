import frappe

def execute():
	query = '''
		update
			`tabTimesheet`
		set
			workflow_state = 'Approved'
		where
			 not workflow_state = "Approved"
	'''
	frappe.db.sql(query)