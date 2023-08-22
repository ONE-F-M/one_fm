import frappe

def execute():
	query = '''
		update
			`tabERF`
		set
			hiring_method = 'Buffet Recruitment'
		where
			hiring_method = 'Bulk Recruitment'
	'''
	frappe.db.sql(query)