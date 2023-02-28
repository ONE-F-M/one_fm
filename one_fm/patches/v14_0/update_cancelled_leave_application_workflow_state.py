import frappe

def execute():
	query = '''
		update
			`tabLeave Application`
		set
			workflow_state = 'Cancelled'
		where
			workflow_state = 'Approved' and status = 'Cancelled'
	'''
	frappe.db.sql(query)
