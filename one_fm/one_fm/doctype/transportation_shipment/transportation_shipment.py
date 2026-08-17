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


# The canvas identifies a card as "TSHIP-<shipment>", sometimes with a direction suffix, so
# what it sends is a card id and not a document name. Both merge endpoints are called
# straight from the canvas and so have to accept either (WI-002078).
def resolve_shipment_names(values) -> list:
	"""Card ids or shipment names in; shipment names out, order and duplicates preserved once."""
	from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
		_shipment_from_card_id,
	)

	names = []
	for value in values or []:
		if not value:
			continue
		name = _shipment_from_card_id(value) or value
		if name not in names:
			names.append(name)
	return names


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

	shipments = resolve_shipment_names(shipments)
	if len(shipments) < 2:
		frappe.throw(
			_("Select at least two shipments to merge into a Mixed trip."),
			title=_("Nothing to Merge"),
		)

	docs = [frappe.get_doc("Transportation Shipment", name) for name in shipments]
	for doc in docs:
		doc.check_permission("write")

	docs.sort(key=arrival_order)
	trip_group = merge_key([doc.name for doc in docs])

	for doc in docs:
		# Remember the way this card travelled before the merge, so leaving the merged trip
		# can put it back. A merge is a scheduling decision made on the canvas; the card's
		# own direction is a fact about the journey it was generated for, and overwriting
		# that without a way back left cards stranded as Mixed once their block was removed.
		#
		# Only recorded on the first merge: merging an already-merged card must not
		# overwrite the original with "Mixed".
		values = {"trip_direction": MIXED, "trip_group": trip_group}
		if doc.trip_direction != MIXED and not doc.pre_merge_trip_direction:
			values["pre_merge_trip_direction"] = doc.trip_direction

		# db_set rather than save: the merge changes header facts and must not re-run
		# apply_routing_type, which would rewrite every rider row from the header and undo
		# per-rider stop locations an OSM card depends on.
		doc.db_set(values, update_modified=True)

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


def _seconds_into_day(value) -> int | None:
	"""A Frappe Time field as seconds past midnight.

	`start_time` comes back as a timedelta, not a number, so the clock arithmetic below has
	to normalise it first - adding minutes to a timedelta raises rather than doing anything
	useful.
	"""
	if value is None:
		return None
	if hasattr(value, "total_seconds"):
		return int(value.total_seconds())
	try:
		return int(value)
	except (TypeError, ValueError):
		return None


def _clock(seconds) -> str:
	"""Seconds past midnight as HH:MM, for the modal to print."""
	if seconds is None:
		return ""
	seconds = int(seconds) % 86400
	return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}"


def _minutes(value) -> int:
	try:
		return max(0, int(value or 0))
	except (TypeError, ValueError):
		return 0


@frappe.whitelist()
def get_merge_preview(shipments, vehicle: str = None, timings=None) -> dict:
	"""What the Merge Trip modal shows before anyone confirms (WI-002078).

	Builds the itinerary the merged run would have, walks it leg by leg, and reports
	whether it fits the vehicle. The leg walk is the same function Route Plan validation
	uses, so the seat count the operator is shown is the one the save will judge them by -
	two implementations would drift and the modal would promise a merge the save refuses.

	Each shipment becomes one stop container. A stop where riders both leave and join is
	two containers, because a drop-off and a boarding are two things the driver does even
	when they happen in one place, and the same holds for a stop the run returns to later.

	`timings` optionally carries the per-leg transit and buffer minutes the operator has
	adjusted, keyed by shipment; the returned arrival and departure stamps are recomputed
	from them so the modal can show the knock-on effect down the run.
	"""
	if isinstance(shipments, str):
		shipments = frappe.parse_json(shipments)
	if isinstance(timings, str):
		timings = frappe.parse_json(timings)

	timings = timings or {}
	names = resolve_shipment_names(shipments)
	if len(names) < 2:
		frappe.throw(_("Select at least two shipments to preview a merge."), title=_("Nothing to Merge"))

	docs = [frappe.get_doc("Transportation Shipment", name) for name in names]
	for doc in docs:
		doc.check_permission("read")
	docs.sort(key=arrival_order)

	limit = (
		frappe.db.get_value("Vehicle", vehicle, "custom_max_passenger_capacity") if vehicle else None
	) or 0

	stops, clock = [], None
	for index, doc in enumerate(docs, start=1):
		boards = (doc.trip_direction or "").strip().upper().startswith("RET")
		adjustment = timings.get(doc.name) or {}
		transit = _minutes(adjustment.get("transit_minutes"))
		buffer_minutes = _minutes(adjustment.get("buffer_minutes"))

		# The first stop anchors the run on its own scheduled time; every later stop is
		# driven from the one before it, so an edit high up the run moves everything after.
		anchor = _seconds_into_day(doc.start_time)
		arrival = anchor if clock is None else clock + transit * 60
		if arrival is None:
			arrival = 0
		departure = arrival + buffer_minutes * 60
		clock = departure

		stops.append({
			"stop_index": index,
			"shipment": doc.name,
			"stop_location": doc.stop_location,
			"headcount": doc.headcount or 0,
			"boards": boards,
			"action": "Boarding" if boards else "Dropping Off",
			"routing_type_badge": doc.routing_type_badge,
			"transit_minutes": transit,
			"buffer_minutes": buffer_minutes,
			"arrival": _clock(arrival),
			"departure": _clock(departure),
		})

	from one_fm.operations.doctype.route_plan.route_plan import leg_occupancy

	peak, worst_leg, per_leg = leg_occupancy(stops)
	for stop, occupancy in zip(stops, per_leg):
		stop["occupancy"] = occupancy
		stop["exceeded"] = bool(limit) and occupancy > limit

	exceeded = bool(limit) and peak > limit

	return {
		"trip_direction": MIXED,
		"vehicle": vehicle,
		"max_passenger_capacity": limit,
		"stops": stops,
		"peak_occupancy": peak,
		"worst_leg": worst_leg,
		"exceeded": exceeded,
		# The modal disables Confirm on this alone, so it is decided here rather than
		# left to the browser to work out from the numbers.
		"can_merge": not exceeded,
		"message": (
			_("Leg {0}: {1}/{2} Seats EXCEEDED").format(worst_leg, peak, limit)
			if exceeded else ""
		),
	}


def unmerge_trip_shipment(name) -> bool:
	"""Put a shipment back the way it travelled before it was merged (WI-002071).

	Called when a card leaves the merged trip - the block is removed from the lane, or the
	plan no longer places it. Without this a card that was merged once stayed Mixed for
	good: it came back to the unassigned pool describing a journey it no longer had, and no
	amount of re-planning restored it.

	Only a card that actually carries a remembered direction is touched, so this is safe to
	call for every shipment a plan drops.
	"""
	original = frappe.db.get_value("Transportation Shipment", name, "pre_merge_trip_direction")
	if not original:
		return False

	frappe.db.set_value(
		"Transportation Shipment",
		name,
		{"trip_direction": original, "trip_group": None, "pre_merge_trip_direction": None},
		update_modified=False,
	)
	return True
