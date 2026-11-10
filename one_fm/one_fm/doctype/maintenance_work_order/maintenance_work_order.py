# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""A maintenance job on an Object.

The derived fields and the SLA clock are calculated by the Calculate Work Order script. The
Maintenance Work Order Lifecycle map records the check-in, closes the SLA and submits; the
Maintenance Work Order SLA Countdown timer advances the live countdown every 5 minutes.
"""

import frappe
from frappe import _
from frappe.model.document import Document

from one_fm.one_fm import processa_rules

RULES = "Calculate Work Order"


class MaintenanceWorkOrder(Document):
	def before_insert(self):
		rules = processa_rules.site_rules(RULES)
		if rules and not rules["initialise"](self):
			frappe.throw(
				_("No active Maintenance Service Level Agreement found for this customer/project. "
				  "Please configure an SLA before creating a Reactive Maintenance Work Order.")
			)

	def before_save(self):
		processa_rules.run_rule(RULES, "calculate", self)

	def validate(self):
		self.validate_priority_against_sla()

	def validate_priority_against_sla(self):
		"""Block a priority that the linked SLA contract does not configure."""
		if not self.sla_master or not self.priority:
			return

		valid_priorities = frappe.get_all(
			"Maintenance SLA Priority",
			filters={"parent": self.sla_master},
			pluck="priority",
		)

		if valid_priorities and self.priority not in valid_priorities:
			frappe.throw(
				_("Selected Priority is not configured within the active client Service Level Agreement.")
			)


@frappe.whitelist()
def get_sla_priorities(sla_master: str):
	"""Return the list of valid priority names for a given SLA contract.

	This is a module-level whitelisted function (not a class method) so it
	can be called from the client without needing direct read permissions
	on the Maintenance SLA Priority child table.
	"""
	if not sla_master:
		return []

	return frappe.get_all(
		"Maintenance SLA Priority",
		filters={"parent": sla_master},
		pluck="priority",
	)
