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

	def set_progress(self):
		progress_wf_list = {'Open': 0, 'Submitted for Applicant Review': 20, 'Applicant Signed and Uploaded': 100,
			'Applicant Not Signed': 40, 'Cancelled': 0}
		if self.workflow_state in progress_wf_list:
			self.progress = progress_wf_list[self.workflow_state]

	def after_insert(self):
		update_onboarding_doc(self)

	def on_submit(self):
		self.set_progress()
		update_onboarding_doc(self)

	def before_cancel(self):
		self.set_progress()

	def on_update_after_submit(self):
		self.set_progress()
		if self.workflow_state == 'Applicant Signed and Uploaded':
			if not self.attach_duty_commencement:
				frappe.throw(_("Attach Signed Duty Commencement!"))
			if not self.reports_to:
				frappe.throw(_("Select reports to user!"))
			else:
				job_offer = frappe.db.get_value('Onboard Employee', self.onboard_employee, 'job_offer')
				if job_offer:
					self.create_employee(job_offer)
		update_onboarding_doc(self)

	def create_employee(self, job_offer):
		employee = make_employee_from_job_offer(job_offer)
		employee.reports_to = self.reports_to
		employee.one_fm_first_name_in_arabic = employee.employee_name
		employee.permanent_address = "Test"
		employee.reports_to = self.reports_to
		employee.save(ignore_permissions=True)

		frappe.db.set_value('Onboard Employee', self.onboard_employee, 'employee', employee.name)

	def on_cancel(self):
		if self.workflow_state == 'Cancelled':
			update_onboarding_doc(self, cancel_oe = True)
		else:
			update_onboarding_doc(self, True)

	def on_trash(self):
		if self.docstatus == 0:
			update_onboarding_doc(self, True)
