import frappe
from frappe import _
from hrms.hr.doctype.job_applicant.job_applicant import *
from one_fm.one_fm.doctype.magic_link.magic_link import authorize_magic_link, send_magic_link

class JobApplicantOverride(JobApplicant):

	def autoname(self):
		pass

	def validate(self):
		super(JobApplicantOverride, self).validate()
		self.set_interview_round_from_erf()

	def set_interview_round_from_erf(self):
		if self.one_fm_erf and not self.interview_rounds:
			# Get interview rounds from ERF
			erf_interview_rounds = frappe.get_all(
				'ERF Interview Round',
				fields = ['interview_round', 'interview_type', 'remarks'],
			 	filters = {'parenttype': 'ERF', 'parent': self.one_fm_erf},
				order_by="idx"
			)

			# Set interview rounds from ERF
			for erf_interview_round in erf_interview_rounds:
				interview_round = self.append('interview_rounds')
				interview_round.interview_round = erf_interview_round.interview_round
				interview_round.interview_type = erf_interview_round.interview_type
				interview_round.remarks = erf_interview_round.remarks


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
