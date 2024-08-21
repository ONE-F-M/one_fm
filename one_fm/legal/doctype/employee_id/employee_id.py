# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from one_fm.hiring.utils import update_onboarding_doc
from frappe.utils import get_url
from one_fm.qr_code_generator import get_qr_code

class EmployeeID(Document):
	def validate(self):
		self.set_progress()
		self.validate_qr_code()

	def validate_qr_code(self):
		if not self.qr_code_image_link:
			self.qr_code_image_link = get_qr_code(get_url(f"/employee-info/{self.employee}"))

	def set_progress(self):
		progress_wf_list = {'Draft': 0, 'Open Request': 20,
			'Request Accepted': 80, 'Request Rejected': 100, 'Completed': 100}
		if self.workflow_state in progress_wf_list:
			self.progress = progress_wf_list[self.workflow_state]

	def after_insert(self):
		update_onboarding_doc(self)

	def on_submit(self):
		update_onboarding_doc(self)

	def before_cancel(self):
		self.set_progress()

	def on_update_after_submit(self):
		self.set_progress()
		update_onboarding_doc(self)

	def on_cancel(self):
		update_onboarding_doc(self, True)

	def on_trash(self):
		if self.docstatus == 0:
			update_onboarding_doc(self, True)
