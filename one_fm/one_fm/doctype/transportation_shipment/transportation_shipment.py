# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

TRIP_REQUEST = "Trip Request"


class TransportationShipment(Document):
	def validate(self):
		self.set_default_status()
		self.apply_trip_request_rules()
		self.populate_from_trip_request()
		self.apply_routing_type()
		self.calculate_headcount()

	def set_default_status(self):
		"""A freshly created shipment always starts life as Unassigned."""
		if not self.status:
			self.status = "Unassigned"

	def apply_trip_request_rules(self):
		"""When the shipment is sourced from a Trip Request the long-term
		Operations Site does not apply — the ad-hoc Stop Location becomes the
		mandatory waypoint instead. The client script hides Operations Site and
		makes Stop Location visible; here we enforce the same rule on save.
		"""
		if self.source_doctype != TRIP_REQUEST:
			return

		# Operations Site is a long-term (shift-derived) concept and is hidden
		# for ad-hoc Trip Request journeys, so clear any stale value.
		self.operations_site = None

		# Default the header Stop Location to the Trip Request destination if the
		# dispatcher has not chosen one explicitly.
		if not self.stop_location and self.source_docname:
			self.stop_location = frappe.db.get_value(
				TRIP_REQUEST, self.source_docname, "destination_location"
			)

		if not self.stop_location:
			frappe.throw(
				_("Stop Location is mandatory when the shipment is sourced from a Trip Request."),
				title=_("Stop Location Required"),
			)

	def populate_from_trip_request(self):
		"""Pull passengers from the linked Trip Request into the employee table.

		Only runs for Trip Request sourced shipments that have no employee rows
		yet, so a dispatcher can also add rows manually without them being wiped.
		"""
		if self.source_doctype != TRIP_REQUEST or not self.source_docname:
			return

		if self.transportation_shipment_employee:
			return

		passengers = frappe.get_all(
			"Trip Request Passenger",
			filters={"parent": self.source_docname, "parenttype": TRIP_REQUEST},
			fields=[
				"employee_id", "employee_name", "accommodation_camp",
				"stop_location", "operations_site",
			],
			order_by="idx asc",
		)

		for passenger in passengers:
			self.append(
				"transportation_shipment_employee",
				{
					"employee_id": passenger.employee_id,
					"employee_name": passenger.employee_name,
					"accommodation": passenger.accommodation_camp,
					"stop_location": passenger.stop_location,
					"operation_site": passenger.operations_site,
				},
			)

	def apply_routing_type(self):
		"""Populate each employee row according to the routing configuration.

		- Direct: copy the parent Accommodation and Stop Location uniformly.
		- OSM (One Site Many Locations): each worker's Stop Location resolves to
		  the shipment waypoint (the Trip Request destination) and Operation Site
		  is looked up from the worker's own profile, so the Route Plan canvas can
		  sequence Stop Index segments under a single Trip Group.
		- OLM (One Location Many Sites): every worker is bound to the header's
		  single Stop Location while each worker's distinct Operation Site is
		  mapped row-by-row for project/capacity tracking.
		"""
		if not self.transportation_shipment_employee:
			return

		routing = self.routing_type_badge

		# Cache employee -> site lookups to avoid N+1 queries.
		site_by_employee = self._get_employee_sites()

		for row in self.transportation_shipment_employee:
			if routing == "Direct":
				# Direct copies the header waypoint uniformly to every rider.
				row.accommodation = self.accommodation
				row.stop_location = self.stop_location
				row.operation_site = self.operations_site or site_by_employee.get(row.employee_id)
			elif routing == "OSM":
				# One Site Many Locations: each rider keeps their own distinct stop
				# location (fallback to the header), but they all share one site.
				row.stop_location = row.stop_location or self.stop_location
				row.operation_site = (
					self.operations_site or row.operation_site or site_by_employee.get(row.employee_id)
				)
			elif routing == "OLM":
				# One Location Many Sites: every rider is bound to the header's single
				# stop location, while each keeps their distinct operations site.
				row.stop_location = self.stop_location
				row.operation_site = row.operation_site or site_by_employee.get(row.employee_id)

	def _get_employee_sites(self) -> dict:
		"""Return {employee_id: site} for every worker on the shipment."""
		employee_ids = [
			row.employee_id for row in self.transportation_shipment_employee if row.employee_id
		]
		if not employee_ids:
			return {}

		rows = frappe.get_all(
			"Employee",
			filters={"name": ["in", list(set(employee_ids))]},
			fields=["name", "site"],
		)
		return {row.name: row.site for row in rows}

	def calculate_headcount(self):
		"""Keep the read-only Headcount in sync with the employee table."""
		self.headcount = len(self.transportation_shipment_employee)
