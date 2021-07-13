# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from one_fm.hiring.utils import update_onboarding_doc
from frappe.utils import today
from frappe import _

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
		update_onboarding_doc(self)

	def on_update(self):
		self.set_progress()
		self.update_on_workflow_state()
		update_onboarding_doc(self)

	def update_on_workflow_state(self):
		if self.workflow_state == "Applicant Signed":
			duty_commencement = frappe.new_doc('Duty Commencement')
			duty_commencement.onboard_employee = self.onboard_employee
			duty_commencement.save(ignore_permissions=True)
		if self.workflow_state == 'Submitted to Legal':
			self.validate_attachments()
		if self.workflow_state == 'Send to Authorised Signatory' and not self.leal_receives_employee_file:
			frappe.throw(_("Is Leal Receives Employee File ?, If yes please mark it!"))
		if self.workflow_state == 'Completed':
			if not self.leal_receives_original_work_contract:
				frappe.throw(_("Is Leal Receives Original Work Contract?, If yes please mark it!"))
			if not self.attach_authorised_signatory_signed_work_contract:
				frappe.throw(_("Attach Authorised Signatory Signed Work Contract!"))

	def validate_attachments(self):
		kuwaiti_nationality = ["Kuwaiti", "Non-Kuwaiti"]
		if self.nationality not in kuwaiti_nationality and not self.original_passport_required:
			frappe.throw(_("Mark Original Passport Required"))
		if self.original_passport_required and self.nationality in kuwaiti_nationality:
			frappe.throw(_("Mark Original Passport Required False for Kuwait/Non-Kuwaiti"))
		if self.original_passport_required and not self.attach_signed_passport_receiving_copy:
			frappe.throw(_("Attach Passport Receiving Copy!"))
		elif self.nationality in kuwaiti_nationality and not self.attach_passport and not self.attach_non_kuwaiti_civil_id:
			frappe.throw(_("Attch Passport or Non-Kuwait CIVIL ID"))

	def on_cancel(self):
		if self.workflow_state == 'Applicant not Signed':
			update_onboarding_doc(self, cancel_oe = True)
		else:
			update_onboarding_doc(self, True)

	def on_trash(self):
		if self.docstatus == 0:
			update_onboarding_doc(self, True)

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
