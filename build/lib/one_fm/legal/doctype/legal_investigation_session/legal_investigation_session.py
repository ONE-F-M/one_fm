# -*- coding: utf-8 -*-
# Copyright (c) 2020, omar jaber and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class LegalInvestigationSession(Document):
	def on_submit(self):
		self.update_session()

	def update_session(self):
		attendees = ""
		for employee in self.session_parties:
			if employee.attended == "Yes":
				attendees += "{emp_name},".format(emp_name=employee.employee_name)

		legal_inv = frappe.get_doc("Legal Investigation", self.legal_investigation_code)
		legal_inv.append("session_summary", {
			"session_datetime": self.session_datetime,
			"subject": self.subject,
			"conducted_by": self.conductor_name,
			"attendees": attendees.rstrip(","),
			"issues": self.notes,
			"attachment": "<a href='{attachment}' target='_blank'>Session Attachment (Click here)</a>".format(attachment=self.attachment)
		})	
		legal_inv.save(ignore_permissions=True)
		print(attendees)

		frappe.db.commit()