# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from one_fm.hiring.utils import update_onboarding_doc
from one_fm.hiring.doctype.work_contract.work_contract import employee_details_for_wc
from frappe.utils import today
from frappe import _

class CandidateOrientation(Document):
	def validate(self):
		if not self.posting_date:
			self.posting_date = today()
		self.set_progress()

	def set_progress(self):
		progress_wf_list = {'Open': 0, 'Informed Applicant': 20, 'Applicant Attended': 40,
			'Applicant Not Attended': 40, 'Cancelled': 100, 'Completed': 100, 'Cancelled': 0}
		if self.workflow_state in progress_wf_list:
			self.progress = progress_wf_list[self.workflow_state]

	def after_insert(self):
		update_onboarding_doc(self)

	def on_submit(self):
		if not self.location and not self.orientation_on:
			frappe.throw(_('To inform applicant, You need to set Location and Orientation On!'))
		self.set_progress()
		update_onboarding_doc(self)

	def before_cancel(self):
		self.set_progress()

	def on_update_after_submit(self):
		self.set_progress()
		update_onboarding_doc(self)
		if self.workflow_state == 'Applicant Attended' and not frappe.db.exists('Work Contract', {'onboard_employee': self.onboard_employee}):
			filters = employee_details_for_wc(frappe.get_doc('Onboard Employee', self.onboard_employee))
			filters['doctype'] = 'Work Contract'
			filters['onboard_employee'] = self.onboard_employee
			wc = frappe.new_doc('Work Contract')
			for filter in filters:
				wc.set(filter, filters[filter])
			wc.save(ignore_permissions=True)
		if self.workflow_state == 'Completed':
			self.validate_check_list()

	def validate_check_list(self):
		if self.candidate_orientation_check_list:
			not_done = False
			for check_list in self.candidate_orientation_check_list:
				if not check_list.done:
					not_done = True
			if not_done:
				frappe.throw(_("Please mark all Done in Check List to Complete the Orientation"))

	def on_cancel(self):
		if self.workflow_state == 'Cancelled':
			update_onboarding_doc(self, cancel_oe = True)
		else:
			update_onboarding_doc(self, True)

	def on_trash(self):
		if self.docstatus == 0:
			update_onboarding_doc(self, True)

def create_candidate_orientation(onboard_employee):
	candidate_orientation = frappe.new_doc('Candidate Orientation')
	candidate_orientation.onboard_employee = onboard_employee.name
	candidate_orientation.save(ignore_permissions=True)
