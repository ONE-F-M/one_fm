import frappe

def execute():
	query = '''
		update
			`tabERF`
		set
			workflow_state = 'Closed'
		where
			status = 'Closed'
	'''
	frappe.db.sql(query)
