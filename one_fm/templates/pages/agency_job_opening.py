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
    fields = ['name', 'status', 'job_title', 'description', 'designation', 'one_fm_job_opening_created', 'allow_easy_apply']
    agency_exists = frappe.db.exists('Agency', {'company_email': frappe.session.user})
    if agency_exists:
        query = '''
            select
                jo.name, jo.status, jo.job_title, jo.description, jo.designation, jo.one_fm_job_opening_created,
                jo.allow_easy_apply
            from
                `tabJob Opening` jo, `tabActive Willing Agency` a
            where
                a.agency = %(agency)s and a.parent=jo.name and jo.status = 'Open' and jo.publish = 1
        '''
        return frappe.db.sql(query.format(), {'agency': agency_exists}, as_dict=True)
