# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, cint, get_datetime, getdate

# Standard start-of-day for a generated maintenance slot (08:00 local time).
DEFAULT_EXECUTION_TIME = "08:00:00"


class MaintenanceScheduleEntry(Document):
	def validate(self):
		self.fetch_object_details()
		self.set_frequency_days()
		self.set_planned_execution_datetime()

	def fetch_object_details(self):
		"""Trace the asset's category and Space -> Floor -> Building -> Site -> Project
		location chain from the master Object record, mirroring Maintenance Work Order.

		Only fills fields that are currently empty so manual overrides are preserved.
		"""
		if not self.object:
			return

		obj = frappe.db.get_value(
			"Object",
			self.object,
			["object_category", "space"],
			as_dict=True,
		)
		if not obj:
			return

		if not self.object_category:
			self.object_category = obj.object_category
		if not self.space:
			self.space = obj.space

		if self.space:
			space = frappe.db.get_value(
				"Space",
				self.space,
				["maintenance_floor", "building_name", "operations_site", "project"],
				as_dict=True,
			)
			if space:
				if not self.maintenance_floor:
					self.maintenance_floor = space.maintenance_floor
				if not self.building:
					self.building = space.building_name
				if not self.operations_site:
					self.operations_site = space.operations_site
				if not self.project:
					self.project = space.project

	def set_frequency_days(self):
		"""Resolve Frequency (Days) from the linked Maintenance Frequency when it
		has not already been populated (the form also fetches this via fetch_from).
		"""
		if self.frequency_days:
			return
		if self.maintenance_frequency:
			self.frequency_days = frappe.db.get_value(
				"Maintenance Frequency", self.maintenance_frequency, "frequency_days"
			)

	def set_planned_execution_datetime(self):
		"""Derive the Planned Execution Datetime for this maintenance slot.

		Base-date resolution order (per user story):
		  1. Object's Last Service Date
		  2. else the Object's Commissioning Date
		  3. else the Object's system Creation Date

		The resolved base date plus Frequency (Days) is set at 08:00 local time.
		Computed only when the datetime is not already set, so a generated slot
		keeps a stable planned time.
		"""
		if self.planned_execution_datetime:
			return
		if not self.object or not self.frequency_days:
			return

		obj = frappe.db.get_value(
			"Object",
			self.object,
			["last_service_date", "commissioning_date", "creation"],
			as_dict=True,
		)
		if not obj:
			return

		base_date = obj.last_service_date or obj.commissioning_date or getdate(obj.creation)
		planned_date = add_days(getdate(base_date), cint(self.frequency_days))
		self.planned_execution_datetime = get_datetime(f"{planned_date} {DEFAULT_EXECUTION_TIME}")
