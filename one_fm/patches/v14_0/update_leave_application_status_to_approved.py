import frappe

def execute():
	query = '''
		update
			`tabLeave Application`
		set
			status = 'Approved'
		where
			workflow_state = 'Approved' and status = 'Open'
	'''
	frappe.db.sql(query)
