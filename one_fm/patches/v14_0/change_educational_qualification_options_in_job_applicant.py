from __future__ import unicode_literals
import frappe

def execute():
	query = '''
		update
			`tabJob Applicant`
		set
			one_fm_educational_qualification = CASE WHEN one_fm_educational_qualification = 'Post Graduate' THEN 'Masters'
                    								WHEN one_fm_educational_qualification = 'Graduate' THEN 'Bachelor' END'''

	frappe.db.sql(query)
	frappe.db.commit()
