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


def own_direction(shipment) -> str:
	"""OUTBOUND or RETURN for one card's own riders, whatever a merge did to the card.

	`trip_direction` stops answering this the moment the card is merged - it reads Mixed,
	which says how the card is *scheduled*, not which way its riders travel.
	`pre_merge_trip_direction` is the record of the journey the card was generated for.
	The same rule the Route Plan save applies, so the modal and the save cannot disagree
	about who is boarding and who is getting off.
	"""
	from one_fm.operations.doctype.route_plan.route_plan import _card_direction

	return _card_direction(shipment.trip_direction, shipment.get("pre_merge_trip_direction"))


def arrival_time(shipment):
	"""When the vehicle reaches this card, as seconds past midnight.

	An outward card is a drop-off, so the vehicle arrives by the shift's start time. A
	return card is a collection, which happens when the shift *ends* - `start_time` on a
	return shipment is the beginning of the shift being collected from, not a journey
	time. This mirrors the canvas, which draws an outward card at start_time and a
	return card at end_time, so the itinerary reads in the order the blocks sit in on
	the lane.
	"""
	start = _seconds_into_day(shipment.start_time)
	if own_direction(shipment) != "RETURN":
		return start

	end = _seconds_into_day(shipment.end_time)
	if end is None:
		return start
	if start is not None and end <= start:
		end += 24 * 3600     # overnight shift: the collection falls the next morning
	return end


def arrival_order(shipment):
	"""Sort key placing shipments in the order the vehicle reaches them.

	A card with no time to sort on goes last rather than first, so an unscheduled card
	cannot silently claim the head of the itinerary. Two cards due at the same moment are
	served drop-off first: the seats one load vacates are what the next load boards into,
	and collecting first reports an overload that never happens. `name` breaks the
	remaining ties so the order is stable across saves.
	"""
	arrival = arrival_time(shipment)
	boards = own_direction(shipment) == "RETURN"
	return (arrival is None, arrival or 0, boards, shipment.name)


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


def _departure_seconds(value):
	"""The departure the dispatcher stated, as seconds past midnight.

	The modal sends a clock string ("05:30" or "05:30:00"), which `_seconds_into_day`
	cannot read - it handles the timedelta a Time column returns, and int("05:30") raises.
	A blank means "nothing stated", which is what makes the run fall back to the time it
	would have backed into.
	"""
	if value is None or value == "":
		return None
	if hasattr(value, "total_seconds"):
		return int(value.total_seconds())
	if isinstance(value, str) and ":" in value:
		parts = value.split(":")
		try:
			hours, minutes = int(parts[0]), int(parts[1])
			seconds = int(parts[2]) if len(parts) > 2 else 0
		except (TypeError, ValueError):
			return None
		return hours * 3600 + minutes * 60 + seconds
	try:
		return int(value)
	except (TypeError, ValueError):
		return None


def _clock_seconds(seconds) -> str:
	"""Seconds past midnight as HH:MM:SS, which is what a Time control accepts.

	`_clock` prints HH:MM for people to read; a Frappe Time field rejects it outright
	("Time 09:00 must be in format: HH:mm:ss"), so the value the modal seeds its
	departure field with has to carry the seconds.
	"""
	if seconds is None:
		return ""
	seconds = int(seconds) % 86400
	return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"


def _clock(seconds) -> str:
	"""Seconds past midnight as HH:MM, for the modal to print."""
	if seconds is None:
		return ""
	seconds = int(seconds) % 86400
	return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}"


# Where the driver's report-time buffer lives. Named away from the manifest's own QOA
# pass/fail fields so the two are never mistaken for one another.
QOA_BUFFER_FIELD = "custom_transportation_qoa_buffer_minutes"


def qoa_buffer_minutes() -> int:
	"""The driver's report-time buffer, in minutes, from HR Settings (WI-002151 AC 1.2).

	One reader for the whole feature - the modal, the block drawer and the manifest all
	print the same QOA time, and a second lookup would be a second answer. Absent or
	unset it is 0, which makes QOA Time equal the departure time and changes nothing.
	"""
	# Guarded on the field existing: the modal must still open on a site that has not
	# run the patch yet, and get_single_value throws rather than returning None.
	if not frappe.get_meta("HR Settings").get_field(QOA_BUFFER_FIELD):
		return 0
	return _minutes(frappe.db.get_single_value("HR Settings", QOA_BUFFER_FIELD))


def _minutes(value) -> int:
	try:
		return max(0, int(value or 0))
	except (TypeError, ValueError):
		return 0


# What the canvas assumes when a stop is chained without an explicit transit time. The
# modal seeds the same number so the itinerary it prints is the one the blocks get drawn
# from - a modal showing 0 while the canvas silently used 30 is a lie the operator only
# discovers on the manifest.
DEFAULT_TRANSIT_MINUTES = 30


def walk_legs(legs, anchor: int, departure=None) -> list:
	"""When the vehicle leaves for each stop and when it reaches it, seconds past midnight.

	One rule, applied here to the itinerary the modal prints and by the canvas to the
	blocks on the lane: a stop's buffer is the dwell before departing towards it and its
	transit is the drive, so a leg runs [departs, arrives]. Every stop after the first is
	driven forward from the stop before it, so an edit high up the run moves everything
	after it.

	The first stop is the one that has nothing to drive from, and there are two ways to
	place it. Given a `departure` the run leaves at that moment and its arrival is
	calculated forward from it - which is what the dispatcher states in the trip modal
	(WI-002151 AC 1.1). Without one it backs into `anchor`, the shift time the card is
	scheduled on, which is how a run reads before anyone has stated a departure and how
	every caller that has no departure to give still gets a sensible itinerary.

	`legs` is [(transit_minutes, buffer_minutes), ...] in stop order. Seconds may run past
	86400: a run that crosses midnight keeps counting, so the day it rolls into is
	recoverable rather than silently wrapped.
	"""
	walked, clock = [], None
	for transit, buffer_minutes in legs:
		if clock is None:
			if departure is None:
				arrives = anchor
				departs = arrives - (buffer_minutes + transit) * 60
			else:
				departs = departure
				arrives = departs + (buffer_minutes + transit) * 60
		else:
			# The leg begins when the bus is released from the stop before it, and its
			# buffer is dwell WITHIN the leg - which is what makes AC 1.1's formula read
			# literally: Arrival = Departure + Buffer + Transit. The process owner's own
			# sample itinerary is walked exactly this way, departure by departure.
			departs = clock
			arrives = departs + (buffer_minutes + transit) * 60
		walked.append((departs, arrives))
		clock = arrives
	return walked


def day_offset(seconds) -> int:
	"""How many whole days past the run's own day a stamp falls (WI-002151 AC 1.6).

	A late run keeps counting past 86400 rather than wrapping, so this is what tells the
	modal and the manifest to print a `(+1 Day)` badge instead of a time that reads as
	though the bus arrived before it left.
	"""
	if seconds is None:
		return 0
	return max(0, int(seconds) // 86400)


def _timings_by_shipment(timings) -> dict:
	"""Per-leg adjustments keyed by shipment, whatever the canvas keyed them by.

	The canvas knows its cards by card id and only learns the shipment name from this
	preview, so it has to be able to seed saved timings before the first render.
	"""
	return {
		(resolve_shipment_names([key]) or [key])[0]: value
		for key, value in (timings or {}).items()
	}


@frappe.whitelist()
def get_merge_preview(shipments, vehicle: str = None, timings=None, departure=None) -> dict:
	"""What the Merge Trip modal shows before anyone confirms (WI-002078).

	Builds the itinerary the merged run would have, walks it leg by leg, and reports
	whether it fits the vehicle. The leg walk is the same function Route Plan validation
	uses, so the seat count the operator is shown is the one the save will judge them by -
	two implementations would drift and the modal would promise a merge the save refuses.

	Each shipment becomes one stop container. A stop where riders both leave and join is
	two containers, because a drop-off and a boarding are two things the driver does even
	when they happen in one place, and the same holds for a stop the run returns to later.

	`timings` optionally carries the per-leg transit and buffer minutes the operator has
	adjusted, keyed by shipment or by card id; the returned departs/arrives stamps are
	walked from them by `walk_legs`, the same rule the canvas re-times the blocks with, so
	an edit high up the run shows its knock-on effect all the way down.
	"""
	if isinstance(shipments, str):
		shipments = frappe.parse_json(shipments)
	if isinstance(timings, str):
		timings = frappe.parse_json(timings)

	timings = _timings_by_shipment(timings)
	names = resolve_shipment_names(shipments)
	# Card id per shipment, so the canvas can stamp what the operator typed back onto
	# the right block: the resolve above is one-way and the mapping is lost after it.
	card_ids = {}
	for value in shipments or []:
		resolved = (resolve_shipment_names([value]) or [value])[0]
		card_ids.setdefault(resolved, value)
	if len(names) < 2:
		frappe.throw(_("Select at least two shipments to preview a merge."), title=_("Nothing to Merge"))

	docs = [frappe.get_doc("Transportation Shipment", name) for name in names]
	for doc in docs:
		doc.check_permission("read")
	docs.sort(key=arrival_order)

	limit = (
		frappe.db.get_value("Vehicle", vehicle, "custom_max_passenger_capacity") if vehicle else None
	) or 0

	legs = []
	for index, doc in enumerate(docs, start=1):
		adjustment = timings.get(doc.name) or {}
		# The first stop is what the run backs into, so it has nothing to drive from.
		default_transit = 0 if index == 1 else DEFAULT_TRANSIT_MINUTES
		legs.append((
			_minutes(adjustment.get("transit_minutes", default_transit)),
			_minutes(adjustment.get("buffer_minutes")),
		))

	anchor = arrival_time(docs[0]) or 0
	departure = _departure_seconds(departure)
	# What the run leaves on before anyone states otherwise: the moment it would have
	# backed into its first stop's shift time. Pre-filling this rather than a blank keeps
	# an untouched trip timed exactly as it is today, so switching the modal to forward
	# calculation does not silently re-time every run on the board.
	first_transit, first_buffer = legs[0]
	default_departure = max(0, anchor - (first_buffer + first_transit) * 60)
	if departure is None:
		departure = default_departure

	walked = walk_legs(legs, anchor, departure=departure)

	# The camp the run belongs to, and the Location that stands for it. Stop 1 leaves
	# from there; every later stop leaves from the stop before it, which is what makes
	# QOA an accommodation-departure fact rather than a per-leg one (AC 1.2).
	base_accommodation = next((doc.accommodation for doc in docs if doc.accommodation), None)
	camp_stop = _camp_stop(docs[0]) if docs else None
	# The readable camp name lives on the shipment, not on Accommodation.
	camp_label = next((doc.accommodation_name for doc in docs if doc.accommodation_name), None) \
		or base_accommodation
	qoa_buffer = qoa_buffer_minutes()

	stops = []
	for index, doc in enumerate(docs, start=1):
		boards = own_direction(doc) == "RETURN"
		transit, buffer_minutes = legs[index - 1]
		departs, arrives = walked[index - 1]
		# Where the bus collects these riders: an outward card loads at its own camp, a
		# return card loads at the site it is collecting from.
		origin = doc.stop_location if boards else (
			_camp_stop(doc) or doc.accommodation_name or doc.accommodation
		)

		# QOA is the driver's report time at a camp, so it belongs to a leg that actually
		# departs one. Riders from two cards at the SAME camp board together once, so only
		# the first of them reports; a run calling at three different camps departs each,
		# which is why the sample itinerary carries three separate report times. The same
		# rule the saved assignment row is stamped with, so the modal and the plan agree.
		previous_camp = docs[index - 2].accommodation if index > 1 else None
		departs_camp = bool(not boards and doc.accommodation and doc.accommodation != previous_camp)
		qoa = _clock(departs - qoa_buffer * 60) if departs_camp else None

		stops.append({
			"stop_index": index,
			"shipment": doc.name,
			"card_id": card_ids.get(doc.name, ""),
			"stop_location": doc.stop_location,
			"origin_location": origin,
			"is_accommodation_origin": departs_camp,
			# Where these riders work, which is not where the bus goes next once a run
			# collects from several camps before dropping anyone.
			"shift_location": doc.stop_location,
			# Filled in below, once every leg's own origin is known.
			"next_stop_location": None,
			"direction": own_direction(doc),
			"headcount": doc.headcount or 0,
			"boards": boards,
			"action": "Boarding" if boards else "Dropping Off",
			"routing_type_badge": doc.routing_type_badge,
			"transit_minutes": transit,
			"buffer_minutes": buffer_minutes,
			"departs": _clock(departs),
			"arrives": _clock(arrives),
			"arrives_day_offset": day_offset(arrives),
			"qoa_time": qoa,
		})

	from one_fm.operations.doctype.route_plan.route_plan import leg_occupancy

	peak, worst_leg, per_leg = leg_occupancy(stops)
	for stop, occupancy in zip(stops, per_leg):
		stop["occupancy"] = occupancy
		stop["exceeded"] = bool(limit) and occupancy > limit

	exceeded = bool(limit) and peak > limit

	# The next stop is the following leg's origin; the last leg drives home to the camp
	# the run started from.
	for position, stop in enumerate(stops):
		stop["next_stop_location"] = (
			stops[position + 1]["origin_location"] if position + 1 < len(stops)
			else (camp_stop or camp_label)
		)

	# AC 1.5: a mixed run ends by taking its return riders home, so its last leg has to be
	# the one that ends at the base camp. Enforced for mixed runs only - a plain outbound
	# run legitimately finishes at a site, and holding those to it would refuse every
	# multi-stop drop-off on the board.
	ends_home = _ends_at_base_camp(docs)
	route_message = "" if ends_home else _(
		"The last leg of a mixed run must be the ride home: end the run on a return card "
		"collecting for {0}, so the bus finishes at the camp rather than at a site."
	).format(camp_label or base_accommodation or _("the base accommodation"))

	return {
		"trip_direction": MIXED,
		"vehicle": vehicle,
		"max_passenger_capacity": limit,
		"stops": stops,
		"peak_occupancy": peak,
		"worst_leg": worst_leg,
		"exceeded": exceeded,
		"departure": _clock(departure),
		"default_departure": _clock(default_departure),
		# What the Time control is seeded with; it refuses anything without seconds.
		"departure_input": _clock_seconds(departure),
		# Raw seconds as well as the clock strings: the canvas moves the blocks by the
		# DIFFERENCE between the two, which is a duration and so needs no timezone
		# conversion. Rebuilding an instant from "05:30" in the browser would.
		"departure_seconds": int(departure),
		"default_departure_seconds": int(default_departure),
		"qoa_buffer_minutes": qoa_buffer,
		"base_accommodation": camp_label or base_accommodation,
		"ends_at_base_camp": ends_home,
		"route_message": route_message,
		# The modal disables Confirm on this alone, so it is decided here rather than
		# left to the browser to work out from the numbers.
		"can_merge": not exceeded and ends_home,
		"message": (
			_("Leg {0}: {1}/{2} Seats EXCEEDED").format(worst_leg, peak, limit)
			if exceeded else ""
		),
	}


def _camp_stop(shipment):
	"""The Location that stands for a card's accommodation camp, or None."""
	if not shipment.accommodation:
		return None
	return frappe.db.get_value(
		"Accommodation", shipment.accommodation, "transport_stop_location"
	)


def _ends_at_base_camp(docs) -> bool:
	"""True when the run's final leg is one that finishes at the base accommodation.

	A return card's `stop_location` is where it *collects*; the camp it is heading for is
	its `accommodation`. So "the final stop location must be the base accommodation camp"
	is a statement about the last leg being a ride home, not about a camp appearing in the
	stop column - no card on the board carries the camp as its stop location, and adding a
	terminal camp stop would be a change to the route model rather than a validation.

	A run that is not mixed is left alone: it has no return riders to take home.
	"""
	directions = {own_direction(doc) for doc in docs}
	if len(directions) < 2:
		return True

	last = docs[-1]
	return own_direction(last) == "RETURN"


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


@frappe.whitelist()
def undo_merge(shipments) -> dict:
	"""Roll a merge back from the canvas (WI-002078).

	The merge is written when the operator confirms it, but the plan is saved a moment
	later and can still be rejected - by an overlapping-trip total, a retention lock, a
	multi-day block-out. The merge was already committed by then, so the cards were left
	Mixed while no plan held them: back in the pool describing a journey they did not
	have. The canvas calls this when the save that follows a merge is refused.

	Reports how many cards were actually restored; a card carrying no remembered
	direction was never merged and is left alone.
	"""
	names = resolve_shipment_names(shipments)
	restored = []
	for name in names:
		if not frappe.db.exists("Transportation Shipment", name):
			continue
		frappe.get_doc("Transportation Shipment", name).check_permission("write")
		if unmerge_trip_shipment(name):
			restored.append(name)

	return {"restored": restored}
