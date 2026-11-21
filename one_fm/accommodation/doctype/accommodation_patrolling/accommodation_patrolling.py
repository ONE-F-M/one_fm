# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class AccommodationPatrolling(Document):
	def before_insert(self):
		self.set_officer_details()

	def set_officer_details(self):
		"""Stamp the creating user, time and Employee shift. Insert only, so later edits keep them."""
		user = frappe.session.user
		self.patrolling_date_and_time = now_datetime()
		self.name_of_security_officer = user
		self.patrol_shift = frappe.db.get_value("Employee", {"user_id": user}, "shift")
		# Links are validated (and fetch_from filled) before before_insert runs, so fill them here.
		self.email_address = frappe.db.get_value("User", user, "email")
		times = self.patrol_shift and frappe.db.get_value(
			"Operations Shift", self.patrol_shift, ["start_time", "end_time"]
		)
		self.shift_time, self.shift_end_time = times or (None, None)

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
