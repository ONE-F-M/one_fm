# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe import _

class MOM(Document):
	def validate(self):
		attendees_count = 0
		for attendee in self.attendees:
			if attendee.attended_meeting:
				attendees_count = attendees_count + 1
				break
		if(attendees_count < 1):
			frappe.throw(_("Please check the attendees present."))

		if self.issues == "Yes" and len(self.action) < 1:
			frappe.throw(_("Please add Action taken to the table."))
		
			
	def after_insert(self):
		if self.issues == "Yes" and len(self.action) > 0:
			for issue in self.action:
				op_task = frappe.new_doc("Operations Task")
				op_task.subject = issue.subject
				op_task.description = issue.description
				op_task.priority = issue.priority
				op_task.save()
			frappe.db.commit()
