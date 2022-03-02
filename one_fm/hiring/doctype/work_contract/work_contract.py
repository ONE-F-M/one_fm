# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from one_fm.hiring.utils import update_onboarding_doc, update_onboarding_doc_workflow_sate
from frappe.utils import today
from frappe import _
from one_fm.utils import sendemail


class WorkContract(Document):
	def validate(self):
		if self.type == 'New Contract' and not self.onboard_employee:
			frappe.throw(_("New Contract Can be Created with Onboarding Reference Only"))
		if self.type == 'Amend Contract' and not self.employee:
			frappe.throw(_("New Contract Can be Created with Employee Reference Only"))
		if not self.posting_date:
			self.posting_date = today()
		self.set_progress()

	def set_progress(self):
		progress_wf_list = {'Open': 0, 'Submitted for Applicant Review': 10, 'Applicant Signed': 20,
			'Applicant not Signed': 100, 'Submitted to Legal': 40, 'Send to Authorised Signatory': 70, 'Completed': 100,
			'Cancelled': 0}
		if self.workflow_state in progress_wf_list:
			self.progress = progress_wf_list[self.workflow_state]

	def after_insert(self):
		update_onboarding_doc_workflow_sate(self)
		update_onboarding_doc(self)
		
	def on_update(self):
		self.set_progress()
		self.update_on_workflow_state()
		update_onboarding_doc(self)
		self.authorized_signatory_user_id = self.fetch_authorized_signatory_user_id()
		

	def update_on_workflow_state(self):
		if self.workflow_state == 'Send to Authorised Signatory':
			self.validate_attachments()
			self.validate_authorized_signatory()
			#email_authority_for_signature(self)
		if self.workflow_state == 'Submitted for Applicant Review':
			#if applicant sign the contract, the workflow changes to "Applicant Signed",
			if self.check_for_applicant_signature():
				self.workflow_state = "Applicant Signed"
				self.save()
		if self.workflow_state == 'Completed':
			fetch_authority_signature(self)

	def validate_attachments(self):
		document_required = ["Civil ID Front","Civil ID Back","Passport Front","Passport Back"]
		for applicant_docs in self.documents:
			document_required.remove(applicant_docs.document_required)
		if len(document_required) > 0:
			frappe.throw(_("Please Attach "+ ' '.join(str(x) for x in document_required)+" !"))

	def validate_authorized_signatory(self):
		if not self.select_authorised_signatory_signed_work_contract:
			frappe.throw(_("Please select Authorized Signatory!"))

	def on_cancel(self):
		if self.workflow_state == 'Applicant not Signed':
			update_onboarding_doc(self, cancel_oe = True)
		else:
			update_onboarding_doc(self, True)

	def on_trash(self):
		if self.docstatus == 0:
			update_onboarding_doc(self, True)
	
	def check_for_applicant_signature(self):
		if self.employee_signature:
			return True
		else:
			return False
	
	@frappe.whitelist()
	def get_authorized_signatory(self):
		authorize_signatory = []
		if self.pam_file_number:
			pam_authorized_signatory = frappe.get_doc("PAM Authorized Signatory List",{'pam_file_number':self.pam_file_number},["*"],as_dict = True)
			pam_auth_sign = pam_authorized_signatory.as_dict()
			for auth_sign in pam_auth_sign["authorized_signatory"]:
				authorize_signatory.append(auth_sign["authorized_signatory_name_english"])
		return authorize_signatory


	def fetch_authorized_signatory_user_id(self):
		if self.select_authorised_signatory_signed_work_contract and self.pam_file_number:
			pam_authorized_signatory = frappe.get_doc("PAM Authorized Signatory List",{'pam_file_number':self.pam_file_number},["authorized_signatory"],as_dict = True)
			pam_auth_sign = pam_authorized_signatory.as_dict()
			for auth_sign in pam_auth_sign["authorized_signatory"]:
				if self.select_authorised_signatory_signed_work_contract == auth_sign["authorized_signatory_name_english"]:
					user_id = auth_sign["user"]
			return user_id


def	fetch_authority_signature(doc):
		if doc.select_authorised_signatory_signed_work_contract and doc.pam_file_number:
			pam_authorized_signatory = frappe.get_doc("PAM Authorized Signatory List",{'pam_file_number':doc.pam_file_number},["authorized_signatory"],as_dict = True)
			pam_auth_sign = pam_authorized_signatory.as_dict()
			for auth_sign in pam_auth_sign["authorized_signatory"]:
				if doc.select_authorised_signatory_signed_work_contract == auth_sign["authorized_signatory_name_english"]:
					signature = auth_sign["signature"]
		doc.authority_signature = signature

@frappe.whitelist()
def get_employee_details_for_wc(type, employee=False, onboard_employee=False):
	if type == 'New Contract':
		if  not onboard_employee:
			return None
		else:
			return employee_details_for_wc(frappe.get_doc('Onboard Employee', onboard_employee))
	if type == 'Amend Contract':
		if not employee:
			return None
		else:
			return employee_details_for_wc(frappe.get_doc('Employee', employee))


def employee_details_for_wc(employee_or_oe):
	details = {}
	working_hours = 8
	details['employee_name'] = employee_or_oe.employee_name
	details['employee_name_in_arabic'] = employee_or_oe.employee_name_in_arabic
	details['passport_number'] = employee_or_oe.passport_number
	details['designation'] = employee_or_oe.designation
	details['effective_from'] = today()
	if employee_or_oe.doctype == 'Employee':
		details['nationality'] = employee_or_oe.one_fm_nationality
		details['civil_id'] = employee_or_oe.one_fm_civil_id
		details['monthly_salary'] = employee_or_oe.one_fm_basic_salary or employee_or_oe.work_permit_salary
		if employee_or_oe.one_fm_erf:
			working_hours = frappe.db.get_value('ERF', employee_or_oe.one_fm_erf, 'shift_hours')
	elif employee_or_oe.doctype == 'Onboard Employee':
		details['nationality'] = employee_or_oe.nationality
		details['civil_id'] = employee_or_oe.civil_id
		details['monthly_salary'] = employee_or_oe.job_offer_total_salary
		if employee_or_oe.erf:
			working_hours = frappe.db.get_value('ERF', employee_or_oe.erf, 'shift_hours')
		if employee_or_oe.job_offer:
			estimated_date_of_joining = frappe.db.get_value('Job Offer', employee_or_oe.job_offer, 'estimated_date_of_joining')
			if estimated_date_of_joining:
				details['effective_from'] = estimated_date_of_joining
	details['working_hours'] = working_hours
	return details


def email_authority_for_signature(doc):
	"""
	This function is to notify the Authorized Signatory and request his action. 
	The Message sent through mail consist of 2 action: Approve and Reject.

	Param: doc -> Work Contract Doc

	It's a action that takes place on update of Leave Application.
	"""
	#If Leave Approver Exist
	print(doc.authorized_signatory_user_id)
	if doc.authorized_signatory_user_id:
		parent_doc = frappe.get_doc('Work Contract', doc.name)
		args = parent_doc.as_dict() #fetch fields from the doc.

		#Fetch Email Template for Leave Approval. The email template is in HTML format.
		email_template = frappe.get_doc("Email Template", "Work Contract Approval",)
		message = frappe.render_template(email_template.response_html, args)
		subject = email_template.subject
		recipient= [doc.authorized_signatory_user_id]
		print(recipient)
		#send Email notification
		try:
			sendemail(
				recipients = recipient,
				sender = frappe.get_doc('User', frappe.session.user).email,
				subject = subject,
				message = message,
				reference_doctype = doc.doctype,
				reference_name = doc.name,
			)
			frappe.msgprint(_("Email sent to {0}").format(doc.select_authorised_signatory_signed_work_contract))
		except frappe.OutgoingEmailError:
			pass