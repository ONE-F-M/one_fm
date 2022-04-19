from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url, getdate, today
from one_fm.one_fm.doctype.magic_link.magic_link import authorize_magic_link, send_magic_link
from one_fm.utils import set_expire_magic_link

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
def create_career_history_from_portal(job_applicant, career_history_details):
    '''
        Method to create Career History from Portal
        args:
            job_applicant: Job Applicant ID
            career_history_details: Career History details as json
        Return Boolean
    '''
    # Create Career History
    career_history = frappe.new_doc('Career History')
    career_history.job_applicant = job_applicant

    career_histories = json.loads(career_history_details)
    for history in career_histories:
        career_history_fields = ['company_name', 'country_of_employment', 'start_date', 'responsibility_one',
            'responsibility_two', 'responsibility_three', 'job_title', 'monthly_salary_in_kwd']

        company = career_history.append('career_history_company')
        for field in career_history_fields:
            company.set(field, history.get(field))

        last_job_title = history.get('job_title')
        last_salary = history.get('monthly_salary_in_kwd')
        for promotion in history.get('promotions'):
            company = career_history.append('career_history_company')
            company.company_name = history.get('company_name')
            company.job_title = last_job_title
            if promotion.get('job_title'):
                company.job_title = promotion.get('job_title')
                last_job_title = promotion.get('job_title')
            company.monthly_salary_in_kwd = last_salary
            if promotion.get('monthly_salary_in_kwd'):
                company.monthly_salary_in_kwd = promotion.get('monthly_salary_in_kwd')
                last_salary = promotion.get('monthly_salary_in_kwd')
            company.start_date = getdate(promotion.get('start_date'))
        if history.get('left_the_company'):
            company.end_date = history.get('left_the_company')
        if history.get('reason_for_leaving_job'):
            company.end_date = today()
            company.why_do_you_plan_to_leave_the_job = history.get('reason_for_leaving_job')

    career_history.save(ignore_permissions=True)
    set_expire_magic_link('Job Applicant', job_applicant, 'Career History')
    return True

@frappe.whitelist()
def send_career_history_magic_link(job_applicant, applicant_name, designation):
    '''
        Method used to send the magic Link for Career History to the Job Applicant
        args:
            job_applicant: ID of the Job Applicant
            applicant_name: Name of the applicant
            designation: Designation applied
    '''
    applicant_email = frappe.db.get_value('Job Applicant', job_applicant, 'one_fm_email_id')
    # Check applicant have an email id or not
    if applicant_email:
        # Email Magic Link to the Applicant
        subject = "Fill your Career History Sheet"
        url_prefix = "/career_history?magic_link="
        msg = "<b>Fill your Career History Sheet by visiting the magic link below</b>\
            <br/>Applicant ID: {0}<br/>Applicant Name: {1}<br/>Designation: {2}</br>".format(job_applicant, applicant_name, designation)
        send_magic_link('Job Applicant', job_applicant, 'Career History', [applicant_email], url_prefix, msg, subject)
    else:
        frappe.throw(_("No Email ID found for the Job Applicant"))
