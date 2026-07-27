# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import formatdate, getdate


class PricingProposal(Document):
	def validate(self):
		self.set_budget_configuration()

	def set_budget_configuration(self):
		"""
		Resolve the Budget Configuration in force at the Date of Inception (WI-001713).

		Only drafts resolve it: validate runs again on submit (with docstatus already 1),
		so the configuration a submitted proposal was priced against stays frozen even if
		a newer configuration is added later.
		"""
		if self.docstatus == 0:
			self.budget_configuration = get_budget_configuration_for_date(self.date_of_inception)
			self.pull_budget_configuration_values()

		if not self.budget_configuration:
			frappe.throw(
				_("No Budget Configuration is effective on or before {0}. Create one before pricing this proposal.").format(
					frappe.bold(formatdate(self.date_of_inception))
					if self.date_of_inception
					else _("the Date of Inception")
				),
				title=_("Budget Configuration Not Found"),
			)


	def pull_budget_configuration_values(self):
		"""
		Copy the resolved configuration's values onto this proposal.

		overhead_cost_percent declares fetch_from budget_configuration.overhead_cost_percentage,
		but Frappe resolves fetch_from in _validate_links(), which runs *before* validate -
		so on the save that first sets budget_configuration the link is still empty and
		nothing is fetched. It would only appear on a later save. Reading it here keeps the
		percentage in step with the configuration from the first save onwards.
		"""
		self.overhead_cost_percent = (
			frappe.db.get_value(
				"Budget Configuration", self.budget_configuration, "overhead_cost_percentage"
			)
			if self.budget_configuration
			else None
		)


def get_budget_configuration_for_date(date_of_inception):
	"""
	Latest Budget Configuration effective on or before date_of_inception.

	No permission check here: this runs inside Pricing Proposal validation, where the
	user is not required to have read access to the Budget Configuration master.
	"""
	if not date_of_inception:
		return None

	return frappe.db.get_value(
		"Budget Configuration",
		{"effective_from": ["<=", getdate(date_of_inception)]},
		"name",
		order_by="effective_from desc",
	)


@frappe.whitelist()
def get_applicable_budget_configuration(date_of_inception: str | None = None) -> str | None:
	"""Resolver for the client script, which refreshes the field when the date changes."""
	frappe.has_permission("Budget Configuration", "read", throw=True)

	return get_budget_configuration_for_date(date_of_inception)
