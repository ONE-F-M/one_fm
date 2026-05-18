# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Space(Document):
	def validate(self):
		self.validate_location_chain()

	def validate_location_chain(self):
		"""Enforce the entire location chain: floor → building → site → project.

		Auto-corrects fetched fields to match the selected maintenance_floor,
		preventing API-level tampering of read-only fields.
		"""
		if not self.maintenance_floor:
			return

		floor = frappe.db.get_value(
			"Maintenance Floor",
			self.maintenance_floor,
			["building_name", "operations_site", "project"],
			as_dict=True,
		)
		if not floor:
			return

		if self.building_name != floor.building_name:
			self.building_name = floor.building_name

		if self.operations_site != floor.operations_site:
			self.operations_site = floor.operations_site

		if self.project != floor.project:
			self.project = floor.project
