from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_url, getdate, today
from one_fm.one_fm.doctype.magic_link.magic_link import authorize_magic_link, send_magic_link
from one_fm.utils import set_expire_magic_link

def get_context(context):
	context.title = _("Career History")
	frappe.clear_cache()

	# Authorize Magic Link
	magic_link = authorize_magic_link(frappe.form_dict.magic_link, 'Job Applicant', 'Career History')
	if magic_link:
		# Find Job Applicant from the magic link
		job_applicant = frappe.db.get_value('Magic Link', magic_link, 'reference_docname')
		context.job_applicant = frappe.get_doc('Job Applicant', job_applicant)
		draft_career_history_exists = frappe.db.exists('Career History', {'job_applicant': job_applicant, 'docstatus': 0})
		if draft_career_history_exists:
			frappe.cache().set('career_history', draft_career_history_exists)
			context.career_history = True
		else:
			frappe.clear_cache()
			frappe.cache().set('career_history', 'career_history')
			context.career_history = False

		# Get Country List to the context to show in the portal
		context.country_list = frappe.get_all('Country', fields=['name'])

@frappe.whitelist(allow_guest=True)
def get_the_company_details(which_company):
	company_details = []
	career_history_id = frappe.cache().get('career_history').decode('utf-8')
	if career_history_id == 'career_history':
		return company_details

	career_history = frappe.get_doc('Career History', career_history_id)
	company = []
	prev_salary = False
	prev_job_title = False
	promotions = 0
	company_no = 0
	which_company = int(which_company)
	for ch_company in career_history.career_history_company:
		if ch_company.company_name not in company:
			promotions = 0
			company_no += 1
			if which_company == company_no:
				prev_salary = ch_company.monthly_salary_in_kwd
				prev_job_title = ch_company.job_title

				company_details.append({'company_name': ch_company.company_name,
				'country_of_employment': ch_company.country_of_employment, 'start_date': ch_company.start_date,
				'monthly_salary_in_kwd': ch_company.monthly_salary_in_kwd, 'job_title': ch_company.job_title,
				'reason_for_leaving_job': ch_company.why_do_you_plan_to_leave_the_job, 'end_date': ch_company.end_date})
			if company_details and len(company_details) > (which_company - 1):
				company_details[which_company-1]['working_now'] = 'Yes'
			company.append(ch_company.company_name)
		else:
			if which_company == company_no:
				promotion = False
				salary_hike = False
				if prev_salary != ch_company.monthly_salary_in_kwd:
					salary_hike = True
				if prev_job_title != ch_company.job_title:
					promotion = True
				if promotion or salary_hike:
					prev_salary = ch_company.monthly_salary_in_kwd
					prev_job_title = ch_company.job_title
					promotions += 1
					promotion_value = 0
					if promotion and salary_hike:
						promotion_value = 1
					elif promotion:
						promotion_value = 2
					elif salary_hike:
						promotion_value = 3
					if 'promotions' not in company_details[company_no-1]:
						company_details[company_no-1]['promotions'] = [
							{
								'promotion_value': promotion_value, 'start_date': ch_company.start_date,
								'monthly_salary_in_kwd': ch_company.monthly_salary_in_kwd, 'job_title': ch_company.job_title,
								'reason_for_leaving_job': ch_company.why_do_you_plan_to_leave_the_job, 'end_date': ch_company.end_date
							}
						]
					else:
						company_details[company_no-1]['promotions'].append({
							'promotion_value': promotion_value, 'start_date': ch_company.start_date,
							'monthly_salary_in_kwd': ch_company.monthly_salary_in_kwd, 'job_title': ch_company.job_title,
							'reason_for_leaving_job': ch_company.why_do_you_plan_to_leave_the_job, 'end_date': ch_company.end_date
						})
		if which_company == company_no and company_details and len(company_details) > (which_company - 1):
			if ch_company.end_date:
				company_details[company_no-1]['end_date'] = ch_company.end_date
				company_details[company_no-1]['working_now'] = 'No'
			if ch_company.why_do_you_plan_to_leave_the_job:
				company_details[company_no-1]['reason_for_leaving_job'] = ch_company.why_do_you_plan_to_leave_the_job


	return company_details


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
	draft_career_history_exists = frappe.db.exists('Career History', {'job_applicant': job_applicant, 'docstatus': 0})
	if draft_career_history_exists:
		career_history = frappe.get_doc('Career History', draft_career_history_exists)
		career_history.career_history_company = []
	else:
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
			if len(promotion) > 0:
				company = career_history.append('career_history_company')
				company.company_name = history.get('company_name')
				company.job_title = last_job_title
				company.start_date = getdate(promotion.get('start_date'))
				if promotion.get('job_title'):
					company.job_title = promotion.get('job_title')
					last_job_title = promotion.get('job_title')
					company.monthly_salary_in_kwd = last_salary
				if promotion.get('monthly_salary_in_kwd'):
					company.monthly_salary_in_kwd = promotion.get('monthly_salary_in_kwd')
					last_salary = promotion.get('monthly_salary_in_kwd')
		if history.get('left_the_company'):
			company.end_date = history.get('left_the_company')
		if history.get('reason_for_leaving_job'):
			company.why_do_you_plan_to_leave_the_job = history.get('reason_for_leaving_job')

	career_history.save(ignore_permissions=True)
	#set_expire_magic_link('Job Applicant', job_applicant, 'Career History')
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
