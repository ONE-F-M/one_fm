from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url
from one_fm.one_fm.doctype.magic_link.magic_link import authorize_magic_link, send_magic_link

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

@frappe.whitelist()
def send_career_history_magic_link(job_applicant):
    '''
        Method used to send the magic Link for Career History to the Job Applicant
        args:
            job_applicant: ID of the Job Applicant
    '''
    applicant_email = frappe.db.get_value('Job Applicant', job_applicant, 'one_fm_email_id')
    # Check applicant have an email id or not
    if applicant_email:
        # Email Magic Link to the Applicant
        subject = "Fill your Career History Sheet"
        url_prefix = "/career_history?magic_link="
        msg = "<b>Fill your Career History Sheet by clciking on the magic link below</b>"
        send_magic_link('Job Applicant', job_applicant, 'Career History', [applicant_email], url_prefix, msg, subject)
    else:
        frappe.throw(_("No Email ID found for the Job Applicant"))
