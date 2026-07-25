# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class BudgetConfiguration(Document):
	def validate(self):
		self.validate_single_enabled()
		self.validate_unique_effective_from()

	def validate_single_enabled(self):
		"""Only one Budget Configuration may be Enabled at a time (WI-001707)."""
		if not self.enabled:
			return

		other = frappe.db.get_value(
			"Budget Configuration",
			{"enabled": 1, "name": ["!=", self.name or ""]},
			"name",
		)
		if other:
			frappe.throw(
				_(
					"Budget Configuration {0} is already Enabled. Uncheck its "
					"'Enabled' flag before enabling this one."
				).format(frappe.bold(other)),
				title=_("Another Budget Configuration is Enabled"),
			)

	def validate_unique_effective_from(self):
		"""'Effective From' is the unique key for a Budget Configuration (WI-001707)."""
		if not self.effective_from:
			return

		other = frappe.db.get_value(
			"Budget Configuration",
			{"effective_from": self.effective_from, "name": ["!=", self.name or ""]},
			"name",
		)
		if other:
			frappe.throw(
				_("A Budget Configuration effective from {0} already exists ({1}).").format(
					frappe.bold(frappe.utils.formatdate(self.effective_from)), frappe.bold(other)
				),
				title=_("Duplicate Effective From"),
			)
