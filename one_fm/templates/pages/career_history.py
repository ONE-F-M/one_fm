from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url
from one_fm.one_fm.doctype.magic_link.magic_link import authorize_magic_link

def get_context(context):
    context.title = _("Career History")

    # Authorize Magic Link
    magic_link = authorize_magic_link(frappe.form_dict.magic_link, 'Job Applicant', 'Career History')
    if magic_link:
        # Find Job Applicant from the magic link
        context.job_applicant = frappe.get_doc('Job Applicant', frappe.db.get_value('Magic Link', magic_link, 'reference_docname'))

    # Get Country List to the context to show in the portal
    context.country_list = frappe.get_all('Country', fields=['name'])

@frappe.whitelist(allow_guest=True)
def create_career_history_from_portal(job_applicant):
    '''
        Method to create Career History from Portal
        args:
            job_applicant: Job Applicant ID
            career_history_details:
        Return Boolean
    '''
    # Create Career History
    return True
