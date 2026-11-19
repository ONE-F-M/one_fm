# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class AccommodationPatrolling(Document):
	def validate(self):
		self.validate_incident_observations()

	def validate_incident_observations(self):
		# Frappe v15 enforces mandatory_depends_on only in the browser.
		for row in self.get("accommodation_patrolling_checklist") or []:
			if row.number_of_incidents == "Yes" and not (row.observations_and_incidents or "").strip():
				frappe.throw(
					_("Row #{0}: Observations and Incidents is mandatory when Number of Incidents is Yes").format(row.idx),
					frappe.MandatoryError,
				)
