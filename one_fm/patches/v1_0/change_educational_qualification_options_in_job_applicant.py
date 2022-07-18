from __future__ import unicode_literals
import frappe

def execute():
	query = '''
		update
			`tabJob Applicant`
		set
			one_fm_educational_qualification = 'Under Graduate'
		where
			one_fm_educational_qualification = 'Undergraduate'
	'''
	frappe.db.sql(query)
