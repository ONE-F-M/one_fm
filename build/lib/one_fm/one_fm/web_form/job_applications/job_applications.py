from __future__ import unicode_literals

import frappe

def get_context(context):
	context.show_sidebar=True
	if frappe.db.exists("Job Applicant", {'one_fm_email_id': frappe.session.user}):
		job_applicant = frappe.get_doc("Job Applicant", {'one_fm_email_id': frappe.session.user})
		context.doc = job_applicant
		frappe.form_dict.new = 0
		frappe.form_dict.name = job_applicant.name
		context.title = job_applicant.applicant_name
		context.no_cache = 1

def get_list_context(context):
	context.get_list = get_job_applicant_list
	context.show_sidebar=True

def get_job_applicant_list(doctype, txt, filters, limit_start, limit_page_length = 20, order_by='modified desc'):
	applicant = get_applicant()
	job_applicant_list = frappe.db.sql("""select * from `tabJob Applicant`
		where name = %s""", applicant, as_dict = True)
	return job_applicant_list

def get_applicant():
	return frappe.get_value("Job Applicant",{"one_fm_email_id": frappe.session.user}, "name")
