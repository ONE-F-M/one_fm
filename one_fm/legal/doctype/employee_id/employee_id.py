# -*- coding: utf-8 -*-
# Copyright (c) 2021, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from one_fm.hiring.utils import update_onboarding_doc
from frappe.utils import global_date_format
import urllib.parse

class EmployeeID(Document):
	def validate(self):
		self.set_progress()
		self.validate_qr_code()

	def validate_qr_code(self):
		if not self.qr_code_image_link:
			chart = "http://chart.googleapis.com/chart?cht=qr&chs=200x200&chl=";
			fields = ['Employee Name', 'Employee Name in Arabic', 'Designation', 'Designation in Arabic', 'Date of Birth',
				'Date of Joining', 'CIVIL ID']
			qr_details = ""
			for field in fields:
				fieldname = field.lower().replace(' ', '_')
				field_value = self.get(fieldname)
				if field_value:
					df = self.meta.get_field(fieldname)
					if df.fieldtype == "Date":
						field_value = global_date_format(field_value)
					qr_details += field+": "+field_value+"\n"
			self.qr_code_image_link = chart+urllib.parse.quote(qr_details)

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
