from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document


def get_context(context):
    context.show_search = True


@frappe.whitelist(allow_guest=True)
def get_gender():
    doc = frappe.get_doc('Gender')
    doc.title = 'Gender'
    doc.save()
    return doc

@frappe.whitelist(allow_guest=True)
def get_job_openings(doctype='Job Opening', txt=None, filters=None, limit_start=0, limit_page_length=20, order_by=None):
	fields = ['name', 'status', 'job_title', 'description', 'designation', 'one_fm_job_opening_created']

	filters = filters or {}
	filters.update({
		'status': 'Open'
	})

	if txt:
		filters.update({
			'job_title': ['like', '%{0}%'.format(txt)],
			'description': ['like', '%{0}%'.format(txt)]
		})

	return frappe.get_all(doctype,
		filters,
		fields,
		start=limit_start,
		page_length=limit_page_length,
		order_by=order_by
	)
