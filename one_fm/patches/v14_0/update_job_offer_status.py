import frappe

def execute():
	query = '''
		update
			`tabJob Offer`
		set
			status = ''
		where
			workflow_state = 'Open' and docstatus = 0 and status = 'Awaiting Response'
	'''
	frappe.db.sql(query)