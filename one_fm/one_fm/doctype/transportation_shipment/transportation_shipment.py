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

		# Default the header Stop Location and the duration/time window from the
		# source Trip Request when the dispatcher has not set them explicitly.
		if self.source_docname:
			trq = frappe.db.get_value(
				TRIP_REQUEST,
				self.source_docname,
				["destination_location", "from_date", "to_date", "departure_time", "return_time"],
				as_dict=True,
			)
			if trq:
				if not self.stop_location:
					self.stop_location = trq.destination_location
				if not self.from_date:
					self.from_date = trq.from_date
				if not self.to_date:
					self.to_date = trq.to_date
				if not self.start_time:
					self.start_time = trq.departure_time
				if not self.end_time:
					self.end_time = trq.return_time

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


MIXED = "Mixed"
RETURN = "Return"
OUTWARD = "Outward"


def merge_key(shipment_names) -> str:
	"""A stable, unique key shared by every shipment in one merged trip (WI-002071).

	Derived from the sorted member names rather than a random token, so merging the
	same set of cards twice produces the same key and a re-run cannot leave two half
	of a trip pointing at different groups. Hashed rather than concatenated because
	the field is Data and a ten-card trip would overflow it.
	"""
	import hashlib

	digest = hashlib.sha1("|".join(sorted(shipment_names)).encode()).hexdigest()
	return f"MIX-{digest[:12]}"


def arrival_order(shipment):
	"""Sort key placing shipments in the order the vehicle reaches them.

	The scheduled arrival is the shipment's own start time; a card without one sorts
	last rather than first, so an unscheduled card cannot silently claim the head of
	the itinerary. `name` breaks ties so the order is stable across saves.
	"""
	return (shipment.start_time is None, shipment.start_time, shipment.name)


@frappe.whitelist()
def merge_trip_shipments(shipments) -> dict:
	"""Merge two or more cards into a single Mixed trip (WI-002071).

	Called by the canvas when a card is dropped onto a block already occupied. Every
	participating shipment becomes `trip_direction = "Mixed"` and receives a shared
	`trip_group`, while each keeps its own Routing Type Badge - Direct, OSM and OLM
	describe how a card's own riders are routed, which merging does not change.

	The returned itinerary is ordered by scheduled arrival, which is the order the
	Route Plan Assignment rows and the manifest both have to be written in.
	"""
	if isinstance(shipments, str):
		shipments = frappe.parse_json(shipments)

	shipments = [name for name in (shipments or []) if name]
	if len(shipments) < 2:
		frappe.throw(
			_("Select at least two shipments to merge into a Mixed trip."),
			title=_("Nothing to Merge"),
		)

	docs = [frappe.get_doc("Transportation Shipment", name) for name in dict.fromkeys(shipments)]
	for doc in docs:
		doc.check_permission("write")

	docs.sort(key=arrival_order)
	trip_group = merge_key([doc.name for doc in docs])

	for doc in docs:
		# db_set rather than save: the merge changes two header facts and must not
		# re-run apply_routing_type, which would rewrite every rider row from the
		# header and undo per-rider stop locations an OSM card depends on.
		doc.db_set({"trip_direction": MIXED, "trip_group": trip_group}, update_modified=True)

	return {
		"trip_group": trip_group,
		"trip_direction": MIXED,
		"itinerary": [
			{
				"shipment": doc.name,
				"stop_index": index,
				"stop_location": doc.stop_location,
				"headcount": doc.headcount,
				"routing_type_badge": doc.routing_type_badge,
				"start_time": doc.start_time,
				"end_time": doc.end_time,
			}
			for index, doc in enumerate(docs, start=1)
		],
	}
