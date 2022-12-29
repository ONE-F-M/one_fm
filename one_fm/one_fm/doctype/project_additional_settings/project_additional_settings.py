# Copyright (c) 2022, omar jaber and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class ProjectAdditionalSettings(Document):
	def validate(self):
		if self.assign_task_from_email:
			if not self.differentiate_assignment_from_email_content_by:
				frappe.throw(_("Select Differentiate Assignment from Email Content by"))
			elif self.differentiate_assignment_from_email_content_by in \
				['Start and End Tag', 'Start and End Tag or Mail to Tag']:
				if not self.start_tag:
					frappe.throw(_("Start Tag is Mandatory!"))
			else:
				self.start_tag = ''
				self.end_tag = ''
		else:
			self.differentiate_assignment_from_email_content_by = ''
			self.start_tag = ''
			self.end_tag = ''
