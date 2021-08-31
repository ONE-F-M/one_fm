# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from one_fm.hiring.utils import update_onboarding_doc, make_employee_from_job_offer
from frappe.utils import today
from frappe import _

class DutyCommencement(Document):
	def validate(self):
		if not self.posting_date:
			self.posting_date = today()
		self.set_progress()
		self.update_salary_details_from_job_offer()

	def update_salary_details_from_job_offer(self):
		if self.salary_details and self.job_offer:
			job_offer = frappe.get_doc('Job Offer', self.job_offer)
			if job_offer.one_fm_salary_details:
				total_salary = 0
				for salary in job_offer.one_fm_salary_details:
					sd = self.append('salary_details')
					sd.salary_component = salary.salary_component
					sd.amount = salary.amount
					if "Basic" in salary.salary_component:
						self.basic_salary = salary.amount
					elif "Transportation" in salary.salary_component:
						self.transportation_salary = salary.amount
					elif "Accommodation" in salary.salary_component:
						self.accommodation_salary = salary.amount
					else:
						self.other_allowances_salary = salary.amount
					total_salary += salary.amount
				self.total_salary = total_salary

	def set_progress(self):
		progress_wf_list = {'Open': 0, 'Submitted for Applicant Review': 20, 'Applicant Signed and Uploaded': 100,
			'Applicant Not Signed': 40, 'Cancelled': 0}
		if self.workflow_state in progress_wf_list:
			self.progress = progress_wf_list[self.workflow_state]

	def after_insert(self):
		update_onboarding_doc(self)

	def on_update(self):
		self.set_progress()
		self.validate_attachments()
		update_onboarding_doc(self)

	def validate_attachments(self):
		if self.workflow_state == 'Applicant Signed and Uploaded':
			if not self.attach_duty_commencement:
				frappe.throw(_("Attach Signed Duty Commencement!"))

	def on_cancel(self):
		if self.workflow_state == 'Cancelled':
			update_onboarding_doc(self, cancel_oe = True)
		else:
			update_onboarding_doc(self, True)

	def on_trash(self):
		if self.docstatus == 0:
			update_onboarding_doc(self, True)
