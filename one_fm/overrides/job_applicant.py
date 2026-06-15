from datetime import datetime, timedelta
import json

import frappe
from frappe import _
from frappe.utils import getdate, get_url_to_form
from hrms.hr.doctype.job_applicant.job_applicant import *
from one_fm.one_fm.doctype.magic_link.magic_link import authorize_magic_link, send_magic_link
from one_fm.processor import sendemail
from one_fm.utils import is_scheduler_emails_enabled

from one_fm.utils import production_domain
from hrms.hr.doctype.job_applicant.job_applicant import create_interview as hrms_create_interview


class JobApplicantOverride(JobApplicant):
	def autoname(self):
		pass

	def update_applicant_name(self):
		"""
		Constructs full applicant name from individual name components.
		Triggered before save when any name field changes.
		"""
		name_parts = [
			self.one_fm_first_name,
			self.one_fm_second_name,
			self.one_fm_third_name,
			self.one_fm_fourth_name,
			self.one_fm_last_name
		]

		# Filter out None and empty strings, join with space
		full_name = " ".join(filter(None, name_parts))

		if full_name and full_name != self.applicant_name:
			self.applicant_name = full_name
			return True
		return False

	def validate(self):
		self.set_hiring_method()
		self.validate_duplicate_application()
		super(JobApplicantOverride, self).validate()
		self.validate_transfer_reminder_date()
		self.update_applicant_name()
		self.convert_name_to_title_case()
		if self.status == 'Open' and self.one_fm_applicant_status == 'Shortlisted':
			self.mark_as_shortlisted_first = True

	def set_hiring_method(self):
		'''
			Method to check if one_fm_hiring_method is not already set and erf is linked to the job applicant
		'''
		# Check if one_fm_hiring_method is not already set and one_fm_erf exists
		if not self.one_fm_hiring_method and self.one_fm_erf:
			# Retrieve the hiring method from the ERF and set it to the one_fm_hiring_method in job applicant
			self.one_fm_hiring_method = frappe.db.get_value("ERF", self.one_fm_erf, "hiring_method")

	def validate_duplicate_application(self):
		'''
			Method to validates that a job applicant is not applying for the same position more than once.
			If the hiring method is not 'Bulk Recruitment', it checks for existing applications with the same
			job title and email ID, but a different name.
			If a duplicate application is found, an error is thrown.
		'''
		if self.one_fm_hiring_method != 'Bulk Recruitment' and self.is_new():
			if frappe.db.exists("Job Applicant", {
				"job_title": self.job_title,
				"one_fm_email_id": self.one_fm_email_id,
				"name": ["!=", self.name]
			}):
				frappe.throw(_("""
					Not allowed to apply for same position again
					<br/>
					Change your email id, if you wish to apply it for different person
				"""))

	def after_insert(self):
		self.notify_recruiter_and_requester_from_job_applicant()
		self.set_interview_rounds_from_erf()

	def notify_recruiter_and_requester_from_job_applicant(self):
		if self.one_fm_erf and self.one_fm_hiring_method == "A la carte Recruitment":
			recipients = []
			erf_details = frappe.db.get_values('ERF', filters={'name': self.one_fm_erf},
				fieldname=["erf_requested_by", "recruiter_assigned", "secondary_recruiter_assigned"], as_dict=True)
			if erf_details and len(erf_details) == 1:
				if erf_details[0].erf_requested_by and erf_details[0].erf_requested_by != 'Administrator':
					recipients.append(erf_details[0].erf_requested_by)
				if erf_details[0].recruiter_assigned:
					recipients.append(erf_details[0].recruiter_assigned)
				if erf_details[0].secondary_recruiter_assigned:
					recipients.append(erf_details[0].secondary_recruiter_assigned)
			designation = frappe.db.get_value('Job Opening', self.job_title, 'designation')
			context = {
				"designation": designation,
				"status": self.status,
				"applicant_name": self.applicant_name,
				"cv": frappe.utils.get_url(self.resume_attachment) if self.resume_attachment else None,
				"passport_type": self.one_fm_passport_type,
				"job_applicant": frappe.utils.get_url(self.get_url()),
				"contact_email": self.one_fm_email_id
			}

			message = frappe.render_template('one_fm/templates/emails/job_application_notification.html', context=context)

			if recipients:
				sendemail(
					recipients=recipients,
					subject='Job Application created for {0}'.format(designation),
					message=message,
					reference_doctype=self.doctype,
					reference_name=self.name,
				)

	def set_interview_rounds_from_erf(self):
		if self.one_fm_erf:
			erf_interview_rounds = frappe.get_all(
				"ERF Interview Round",
				fields = ['interview_round', 'interview_type'],
				filters={
					"parent": self.one_fm_erf, "parenttype": "ERF"
				}
			)

			if erf_interview_rounds and len(erf_interview_rounds) > 0:
				for erf_interview_round in erf_interview_rounds:
					interview_rounds = self.append('interview_rounds')
					interview_rounds.interview_round = erf_interview_round.interview_round
					interview_rounds.interview_type = erf_interview_round.interview_type
				self.save(ignore_permissions=True)

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
				if datetime.strptime(str(self.custom_transfer_reminder_date), "%Y-%m-%d") <= datetime.strptime(str(getdate()), "%Y-%m-%d"):
					frappe.throw(_("Oops! You can't choose a date in the past or today. Please select a future date."))

			except Exception as e:
				frappe.log_error(message=frappe.get_traceback(), title="Error while validating date of local transfer in Job Applicant")
				...

	def convert_name_to_title_case(self):
		name_fields = ['applicant_name', 'one_fm_first_name', 'one_fm_second_name', 'one_fm_third_name', 'one_fm_fourth_name', 'one_fm_last_name']
		for name_attr in name_fields:
			current_name = getattr(self, name_attr, '')
			if current_name is not None:
				setattr(self, name_attr, current_name.title())

	def on_update(self):
		self.sync_fields_to_linked_documents()

	def sync_fields_to_linked_documents(self):
		"""
		Synchronizes specified fields from Job Applicant to linked Job Offers and Onboard Employee records.
		Only updates documents that are not cancelled (docstatus < 2 for Job Offer, any for Onboard Employee).
		"""
		job_offer_fields = {
			"applicant_name": "applicant_name",
			"one_fm_nationality": "nationality"
		}
		job_offer_changed_fields = [field for field in job_offer_fields.keys() if self.has_value_changed(field)]

		onboard_employee_field_mapping = self.get_onboard_employee_field_mapping()
		onboard_employee_changed_fields = [field for field in onboard_employee_field_mapping.keys() if self.has_value_changed(field)]

		if job_offer_changed_fields:
			job_offers = self.get_linked_job_offers()
			self.update_linked_documents(job_offers, "Job Offer", job_offer_fields, job_offer_changed_fields)

		if onboard_employee_changed_fields:
			onboard_employees = self.get_linked_onboard_employees()
			self.update_linked_documents(onboard_employees, "Onboard Employee", onboard_employee_field_mapping, onboard_employee_changed_fields)

	def get_onboard_employee_field_mapping(self):
		return {
			"one_fm_first_name_in_arabic": "first_name_in_arabic",
			"one_fm_second_name_in_arabic": "second_name_in_arabic",
			"one_fm_third_name_in_arabic": "third_name_in_arabic",
			"one_fm_fourth_name_in_arabic": "fourth_name_in_arabic",
			"one_fm_last_name_in_arabic": "last_name_in_arabic",
			"applicant_name": "employee_name",
			"one_fm_gender": "gender",
			"one_fm_date_of_birth": "date_of_birth",
			"one_fm_nationality": "nationality",
			"one_fm_passport_number": "passport_number",
			"one_fm_passport_issued": "passport_issued",
			"one_fm_passport_expire": "passport_expire"
		}

	def get_linked_job_offers(self):
		return frappe.get_all(
			"Job Offer",
			filters={
				"job_applicant": self.name,
				"docstatus": ["<", 2]  # Draft or Submitted, not Cancelled
			},
			pluck="name"
		)

	def update_linked_documents(self, linked_docs, linked_doctype, field_mappings, changed_fields):
		for linked_doc_name in linked_docs:
			try:
				linked_doc = frappe.get_doc(linked_doctype, linked_doc_name)
				updated = False
				for job_applicant_field in changed_fields:
					linked_doc_field = field_mappings[job_applicant_field]
					if hasattr(linked_doc, linked_doc_field):
						new_value = self.get(job_applicant_field)
						if linked_doc.get(linked_doc_field) != new_value:
							linked_doc.set(linked_doc_field, new_value)
							updated = True

				if updated:
					linked_doc.flags.ignore_validate_update_after_submit = True
					linked_doc.flags.ignore_mandatory = True
					linked_doc.save(ignore_permissions=True)

			except Exception as e:
				frappe.log_error(
					title=f"Failed to sync to {linked_doctype} {linked_doc_name}",
					message=f"Error: {str(e)}\n\n{frappe.get_traceback()}"
				)

	def sync_to_onboard_employee(self, field_mappings, changed_fields):
		"""Sync changes to Onboard Employee documents"""
		onboard_employees = self.get_linked_onboard_employees()

		for onboard_emp_name in onboard_employees:
			try:
				onboard_emp = frappe.get_doc("Onboard Employee", onboard_emp_name)
				updated = False

				for job_applicant_field in changed_fields:
					oe_field = field_mappings[job_applicant_field][1]
					if hasattr(onboard_emp, oe_field):
						new_value = self.get(job_applicant_field)
						if onboard_emp.get(oe_field) != new_value:
							onboard_emp.set(oe_field, new_value)
							updated = True

				if updated:
					onboard_emp.flags.ignore_validate_update_after_submit = True
					onboard_emp.flags.ignore_mandatory = True
					onboard_emp.save(ignore_permissions=True)

			except Exception as e:
				frappe.log_error(
					title=f"Failed to sync to Onboard Employee {onboard_emp_name}",
					message=f"Error: {str(e)}\n\n{frappe.get_traceback()}"
				)
	def get_linked_onboard_employees(self):
		return frappe.get_all(
			"Onboard Employee",
			filters={
				"job_applicant": self.name
			},
			pluck="name"
		)

def notify_hr_manager_about_local_transfer() -> None:
	if production_domain() and is_scheduler_emails_enabled():
		NotifyLocalTransfer().notify_hr_manager_recruiter()

class NotifyLocalTransfer:

	def __init__(self) -> None:
		self.today = datetime.strptime(str(getdate()), "%Y-%m-%d")
		self.thirty = self.today - timedelta(days=30)
		self.sixty = self.today - timedelta(days=60)
		self.ninety = self.today - timedelta(days=90)

	@property
	def _iterable_of_dates(self) -> tuple:
		return (str(self.today), str(self.thirty), str(self.sixty), str(self.ninety))

	def get_job_applicant_with_local_transfers(self) -> dict:
		return frappe.db.sql(f"""
								SELECT name, one_fm_first_name, one_fm_last_name, one_fm_erf
								FROM `tabJob Applicant`
								WHERE one_fm_is_transferable = 'Later'
								AND custom_transfer_reminder_date IN {self._iterable_of_dates};
								""",  as_dict=True)


	@staticmethod
	def get_assigned_recruiter(erf: str) -> str | None:
		return frappe.db.get_value("ERF", erf, "recruiter_assigned")

	@property
	def _default_hiring_manager(self) -> str | None:
		return frappe.db.get_single_value('Hiring Settings', 'default_hr_manager')

	def notify_hr_manager_recruiter(self) -> None:
		try:
			hr_manager = self._default_hiring_manager
			job_applicants = self.get_job_applicant_with_local_transfers()
			if job_applicants:
				for obj in job_applicants:
					receivers = [hr_manager, self.get_assigned_recruiter(erf=obj.get("one_fm_erf", ""))]
					if receivers:
						data = dict(
							applicant_name=f'{obj.get("one_fm_first_name", "")} {obj.get("one_fm_last_name", "")}',
							document_name=obj.get("name"),
							doc_url=get_url_to_form("Job Applicant", obj.get('name'))
						)
						title = f"Local Residency Transfer: {data.get('applicant_name', '')}"
						msg = frappe.render_template('one_fm/templates/emails/notify_recruiter_about_local_transfer.html', context=data)
						sendemail(recipients=receivers, subject=title, content=msg)
		except:
			frappe.log_error(message=frappe.get_traceback(), title="Error while sending notification of local transfer")

@frappe.whitelist()
def create_interview(doc,interview_round):
	interview = hrms_create_interview(doc, interview_round)
	if json.loads(doc)["one_fm_hiring_method"]  == "A la carte Recruitment":
		interview.custom_hiring_method = json.loads(doc)["one_fm_hiring_method"]
		interview.from_time = None
		interview.to_time = None
	return interview

@frappe.whitelist()
def change_applicant_erf(job_applicant, old_erf, new_erf):
	if not frappe.db.exists("Job Applicant", job_applicant):
		return
	if not frappe.db.exists("ERF", new_erf):
		return

	erf_in_job_applicant = frappe.db.get_value("Job Applicant", job_applicant, "one_fm_erf")
	if erf_in_job_applicant != old_erf:
		return

	job_applicant_obj = frappe.get_doc("Job Applicant", job_applicant)
	new_erf_obj = frappe.get_doc("ERF", new_erf)

	job_title = frappe.db.get_value("Job Opening", {'one_fm_erf': new_erf})
	designation = frappe.db.get_value("Job Opening", job_title, "designation")

	job_applicant_obj.update({
		"one_fm_erf": new_erf,
		"job_title": job_title,
		"designation": designation,
		"department": new_erf_obj.department,
		"project": new_erf_obj.project,
		"one_fm_hiring_method": new_erf_obj.hiring_method,
		"interview_round": new_erf_obj.interview_round
	})

	job_applicant_obj.flags.ignore_mandatory = True
	job_applicant_obj.save(ignore_permissions=True)

	job_offer = frappe.db.exists('Job Offer', {'job_applicant': job_applicant, 'docstatus': ['<', 2]})
	if job_offer:
		update_job_offer_with_erf_change(job_offer, job_applicant_obj, new_erf_obj, new_erf)

def update_job_offer_with_erf_change(job_offer, job_applicant_obj, new_erf_obj, new_erf):
	operations_shift = {"project": "", "shift_type": "", "site": ""}
	if new_erf_obj.operations_shift:
		operations_shift = frappe.db.get_value(
			"Operations Shift",
			new_erf_obj.operations_shift,
			["project", "shift_type", "site"],
			as_dict=True
		)

	frappe.db.sql("""
		UPDATE
			`tabJob Offer`
		SET
			employment_type = %s,
			applicant_name = %s,
			day_off_category = %s,
			number_of_days_off = %s,
			designation = %s,
			department = %s,
			one_fm_erf = %s,
			shift_working = %s,
			operations_shift = %s,
			project = %s,
			default_shift = %s,
			operations_site = %s
		WHERE
			name = %s
	""", (
		job_applicant_obj.employment_type,
		job_applicant_obj.applicant_name,
		job_applicant_obj.day_off_category,
		job_applicant_obj.number_of_days_off,
		job_applicant_obj.designation,
		job_applicant_obj.department,
		new_erf,
		new_erf_obj.shift_working,
		new_erf_obj.operations_shift,
		operations_shift["project"],
		operations_shift["shift_type"],
		operations_shift["site"],
		job_offer
	))
