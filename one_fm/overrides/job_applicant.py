from datetime import datetime

import frappe
from frappe import _
from frappe.utils import getdate, get_url_to_form
from hrms.hr.doctype.job_applicant.job_applicant import *
from one_fm.one_fm.doctype.magic_link.magic_link import authorize_magic_link, send_magic_link
from one_fm.processor import sendemail

class JobApplicantOverride(JobApplicant):

	def autoname(self):
		pass

	def validate(self):
		super(JobApplicantOverride, self).validate()
		# self.validate_transfer_reminder_date()


	@frappe.whitelist()
	def send_applicant_doc_magic_link(self):
		'''
			Method used to send the magic Link for Get More Details from the Job Applicant
			args:
				job_applicant: ID of the Job Applicant
				applicant_name: Name of the applicant
				designation: Designation applied
		'''
		job_applicant = frappe.form_dict.job_applicant
		applicant_name = frappe.form_dict.applicant_name
		designation = frappe.form_dict.designation
		applicant_email = frappe.db.get_value('Job Applicant', job_applicant, 'one_fm_email_id')
		# Check applicant have an email id or not
		if applicant_email:
			# Email Magic Link to the Applicant
			subject = "Fill More Details"
			url_prefix = "/magic_link?magic_link="
			msg = "<b>Greetings, you applied for a role at One Facilities Management.<br>Please fill more information like your passport detail by clicking on the link below.</b>\
				<br/>Applicant ID: {0}<br/>Applicant Name: {1}<br/>Designation: {2}</br>".format(job_applicant, applicant_name, designation)
			send_magic_link('Job Applicant', job_applicant, 'Job Applicant', [applicant_email], url_prefix, msg, subject)
		else:
			frappe.throw(_("No Email ID found for the Job Applicant"))

	def validate_transfer_reminder_date(self):
		if self.custom_transfer_reminder_date:
			try:
				if datetime.strptime(self.custom_transfer_reminder_date, "%Y-%m-%d") <= datetime.strptime(str(getdate()), "%Y-%m-%d"):
					frappe.throw(_("Oops! You can't choose a date in the past or today. Please select a future date."))

			except Exception as e:
				frappe.log_error(frappe.get_traceback(), "Error while validating date of local transfer in Job Applicant")
				...



def notify_hr_manager_about_local_transfer():
	print("Oya na")
	return NotifyLocalTransfer().get_job_applicant_with_local_transfers()

class NotifyLocalTransfer:

	def __init__(self):
		...


	def get_job_applicant_with_local_transfers(self):
		job_applicants = frappe.db.sql("""
										SELECT name, one_fm_first_name, one_fm_last_name, one_fm_erf
										FROM `tabJob Applicant`
										WHERE 
											one_fm_is_transferable = 'Later'
											AND (DATE(custom_transfer_reminder_date) = CURDATE() 
												OR DATEDIFF(CURDATE(), DATE(custom_transfer_reminder_date)) IN (-30, -60, -90)
											);
									""", as_dict=True)
		return job_applicants
	

	@staticmethod
	def get_assigned_recruiter(erf: str) -> str:
		return frappe.db.get_value("ERF", erf, "recruiter_assigned")
	
	@property
	def default_hiring_manager(self):
		return frappe.db.get_single_value('Hiring Settings', 'default_hr_manager')
	
	def notify_hr_manager_recruiter(self):
		hr_manager = self.default_hiring_manager
		job_applicants = self.get_job_applicant_with_local_transfers()
		if job_applicants:
			for obj in job_applicants:
				receivers = [hr_manager, self.get_assigned_recruiter(erf=obj.get("one_fm_erf", ""))]
				if receivers:
					data = dict(
						applicant_name_name=f'{obj.get("one_fm_first_name", "")} {obj.get("one_fm_first_name", "")}',
						document_name=obj.get("name"),
						doc_url=get_url_to_form("Job Applicant", obj.get('name'))
					)
					title = f"Local Residency Transfer: {data.get('applicant_name', '')}"
					msg = frappe.render_template('one_fm/templates/emails/notify_recruiter_about_local_transfer..html', context=data)
					# sendemail(recipients=receivers, subject=title, content=msg)

