# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class DMSDocumentType(Document):
	def validate(self):
		self.check_source_guideline()

	def check_source_guideline(self):
		"""The source guideline must be an active Guideline; the picker filter only runs in the browser."""
		if not self.source_guideline:
			return
		kind, state = frappe.db.get_value(
			"Document Register", self.source_guideline, ["document_type", "lifecycle_state"]
		)
		if kind != "Guideline" or state != "Active":
			frappe.throw(
				_("Source Guideline must be an active Guideline. {0} is a {1} that is {2}.").format(
					frappe.bold(self.source_guideline), kind, state
				),
				title=_("Not an active Guideline"),
			)
