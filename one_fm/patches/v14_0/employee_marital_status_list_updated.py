import frappe

def execute():
	query = '''
		update
			`tabEmployee`
		set
			marital_status = 'Unmarried'
		where
			marital_status = 'Single'
	'''
	frappe.db.sql(query)

	query = '''
		update
			`tabEmployee`
		set
			marital_status = 'Widow'
		where
			marital_status = 'Widowed'
	'''
	frappe.db.sql(query)

	query = '''
		update
			`tabEmployee`
		set
			marital_status = 'Divorce'
		where
			marital_status = 'Divorced'
	'''
	frappe.db.sql(query)
