# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class MaintenanceScenario(Document):
	def validate(self):
		self.validate_unique_scenario_per_client()

	def validate_unique_scenario_per_client(self):
		"""One priority per scenario per client.

		The scenario is what a client picks on the portal and the priority is what the
		system derives from it, so a second record for the same pair would make that
		derivation ambiguous.
		"""
		duplicate = frappe.db.exists(
			"Maintenance Scenario",
			{
				"client": self.client,
				"scenario_name": self.scenario_name,
				"name": ("!=", self.name),
			},
		)

		if duplicate:
			frappe.throw(
				_("{0} already has a scenario for {1}: {2}").format(
					frappe.bold(self.client),
					frappe.bold(self.scenario_name),
					frappe.get_desk_link("Maintenance Scenario", duplicate),
				)
			)


def get_scenario_priority(client: str, scenario_name: str) -> str | None:
	"""The priority tier behind a scenario, for the client who reported it.

	Returned rather than sent from the browser: the point of scenarios is that an
	external client cannot choose the priority directly (WI-001802).
	"""
	if not (client and scenario_name):
		return None

	return frappe.db.get_value(
		"Maintenance Scenario", {"client": client, "scenario_name": scenario_name}, "priority"
	)
