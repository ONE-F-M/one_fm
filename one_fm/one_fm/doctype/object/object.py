# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today


class Object(Document):
	def validate(self):
		self.validate_commissioning_date()
		self.set_default_last_service_date()
		self.validate_location_chain()

	def before_save(self):
		self.fetch_template_parts()

	def on_submit(self):
		"""Kick off preventive maintenance automation the moment a brand-new
		Maintenance Object is submitted.

		The Build Schedule and Catch Immediate Work routines run in the
		background (enqueued after commit so the schedule slots reference a
		persisted Object) and are de-duplicated per object.
		"""
		frappe.enqueue(
			"one_fm.one_fm.doctype.maintenance_schedule_entry.maintenance_schedule_entry.process_object_schedule",
			queue="short",
			object_name=self.name,
			enqueue_after_commit=True,
			job_id=f"maintenance-schedule-{self.name}",
			deduplicate=True,
		)

	def validate_commissioning_date(self):
		"""Ensure the commissioning date is not in the future."""
		if self.commissioning_date and getdate(self.commissioning_date) > getdate(today()):
			frappe.throw(
				_("Commissioning Date cannot be in the future. Got: {0}").format(
					frappe.format(self.commissioning_date, {"fieldtype": "Date"})
				)
			)

	def set_default_last_service_date(self):
		"""Default last_service_date to commissioning_date if no service has been performed."""
		if self.commissioning_date and not self.last_service_date:
			self.last_service_date = self.commissioning_date

	def validate_location_chain(self):
		"""Enforce the full location chain: space → floor → building → site → project.

		Auto-corrects read-only fetched fields to prevent API-level tampering.
		"""
		if not self.space:
			return

		space = frappe.db.get_value(
			"Space",
			self.space,
			["maintenance_floor", "building_name", "operations_site", "project"],
			as_dict=True,
		)
		if not space:
			return

		if self.floor != space.maintenance_floor:
			self.floor = space.maintenance_floor

		if self.building != space.building_name:
			self.building = space.building_name

		if self.operations_site != space.operations_site:
			self.operations_site = space.operations_site

		if self.project != space.project:
			self.project = space.project

	def fetch_template_parts(self):
		"""Fetch parts from Object Template into Object Items if the table is empty.

		Only fetches when template is set and object_items is empty,
		allowing the user to keep their manual edits.
		"""
		if not self.object_template:
			return

		if self.object_items:
			return

		template_items = frappe.get_all(
			"Object Template Items",
			filters={"parent": self.object_template},
			fields=["item_name", "description"],
			order_by="idx asc",
		)

		for item in template_items:
			self.append("object_items", {
				"item_name": item.item_name,
				"description": item.description,
			})
