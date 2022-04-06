from __future__ import unicode_literals

import frappe

def get_context(context):
	context.read_only = 1

def get_list_context(context):
	# context.row_template = "one_fm/one_fm/web_form/career_history/career_history_row.html"
	context.get_list = get_career_history_list
	context.show_sidebar=True

def get_career_history_list(doctype, txt, filters, limit_start, limit_page_length = 20, order_by='modified desc'):
	applicant = get_applicant()
	career_history = frappe.db.sql("""select * from `tabCareer History`
		where job_applicant = %s""", applicant, as_dict = True)
	return career_history


def get_applicant():
	return frappe.get_value("Job Applicant",{"one_fm_email_id": frappe.session.user}, "name")

def applicant_has_website_permission(doc, ptype, user, verbose=False):
    if doc.job_applicant == get_applicant():
        return True
    else:
        return False
