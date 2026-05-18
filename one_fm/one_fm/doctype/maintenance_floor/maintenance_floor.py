# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class MaintenanceFloor(Document):
	def validate(self):
		self.validate_location_chain()

	def validate_location_chain(self):
		"""Enforce operations_site and project match the selected building.

		These fields are read-only on the client but can be tampered via API.
		Auto-correct them to the building's values.
		"""
		if not self.building_name:
			return

		building = frappe.db.get_value(
			"Building", self.building_name, ["operations_site", "project"], as_dict=True
		)
		if not building:
			return

		if self.operations_site != building.operations_site:
			self.operations_site = building.operations_site

		if self.project != building.project:
			self.project = building.project
