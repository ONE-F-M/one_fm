# -*- coding: utf-8 -*-
# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class DocumentRequest(Document):
	def validate(self):
		self.set_requester_defaults()
		self.check_approver_resolved()
		self.apply_reference_document_defaults()

	def set_requester_defaults(self):
		if not self.requester:
			employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
			if employee:
				self.requester = employee

	def check_approver_resolved(self):
		if self.requester and not self.approver:
			frappe.throw(
				_(
					"Could not resolve an approver for {0} — their Employee record has no "
					"'Reports To' (line manager) set. Set it on the Employee record first."
				).format(self.requester)
			)

	def apply_reference_document_defaults(self):
		if self.request_action == "Create" or not self.reference_document:
			return
		document_type, title = frappe.db.get_value(
			"AI Reference Index", self.reference_document, ["document_type", "title"]
		)
		self.document_type = document_type
		if not self.title:
			self.title = title
