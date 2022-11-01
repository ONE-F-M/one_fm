import frappe

def execute():
	query = '''
		update
			`tabJob Applicant`
		set
			one_fm_marital_status = 'Unmarried'
		where
			one_fm_marital_status = 'Single'
	'''
	frappe.db.sql(query)

	query = '''
		update
			`tabJob Applicant`
		set
			one_fm_marital_status = 'Widow'
		where
			one_fm_marital_status = 'Widowed'
	'''
	frappe.db.sql(query)

	query = '''
		update
			`tabJob Applicant`
		set
			one_fm_marital_status = 'Divorce'
		where
			one_fm_marital_status = 'Divorced'
	'''
	frappe.db.sql(query)
