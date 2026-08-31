# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

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

	def on_update(self):
		self.refresh_plan_headcounts()

	def refresh_plan_headcounts(self):
		"""Push a changed headcount out to the plan rows that placed this card (#6818).

		A Route Plan Assignment row stores the headcount taken when the card was dropped.
		The seat walk reads the shipment now, so the stored figure no longer decides
		anything - but it is still what the row, the report and anyone reading the plan
		sees, and a row saying 27 beside a card carrying 28 is how the over-capacity trip
		went unnoticed in the first place. Written straight to the rows: a Route Plan is
		submitted-and-amended, and re-saving one from here would fight that.
		"""
		if not self.has_value_changed("headcount"):
			return

		rows = frappe.get_all(
			"Route Plan Assignment",
			filters={
				"transportation_shipment": self.name,
				"headcount": ["!=", cint(self.headcount)],
				# A camp leg carries no riders of its own; giving it this card's count
				# would have it counted twice by anything that sums the column.
				"is_camp_leg": 0,
			},
			pluck="name",
		)
		for row in rows:
			frappe.db.set_value(
				"Route Plan Assignment", row, "headcount", cint(self.headcount),
				update_modified=False,
			)


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


def run_direction(docs) -> str:
	"""The direction of a merged run: Mixed only when its cards disagree.

	Two outbound cards on one bus is still an outbound run - the bus loads at a camp and
	drops at two sites, which is what a multi-stop trip has always been. Writing Mixed
	over it would say the run carries riders both ways, colour the block as a handover
	and, worse, stamp `pre_merge_trip_direction` on cards that never changed direction -
	so leaving the run would "restore" a direction they already had.

	Mixed is reserved for what it means: one run doing both journeys.
	"""
	own = {own_direction(doc) for doc in docs}
	if len(own) != 1:
		return MIXED
	return RETURN if own.pop() == "RETURN" else OUTWARD


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
	direction = run_direction(docs)

	for doc in docs:
		# Remember the way this card travelled before the merge, so leaving the merged trip
		# can put it back. A merge is a scheduling decision made on the canvas; the card's
		# own direction is a fact about the journey it was generated for, and overwriting
		# that without a way back left cards stranded as Mixed once their block was removed.
		#
		# Only recorded on the first merge: merging an already-merged card must not
		# overwrite the original with "Mixed".
		values = {"trip_direction": direction, "trip_group": trip_group}
		if direction == MIXED and doc.trip_direction != MIXED and not doc.pre_merge_trip_direction:
			values["pre_merge_trip_direction"] = doc.trip_direction

		# db_set rather than save: the merge changes header facts and must not re-run
		# apply_routing_type, which would rewrite every rider row from the header and undo
		# per-rider stop locations an OSM card depends on.
		doc.db_set(values, update_modified=True)

	return {
		"trip_group": trip_group,
		"trip_direction": direction,
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

# How far apart an outward shift's start and a return shift's end may sit and still read
# as a handover (WI-002171 AC 3.1: "matches or stays around couple of hours"). The same
# two hours the canvas uses to decide which runs are near enough to chain.
SHIFT_ALIGNMENT_TOLERANCE_SECONDS = 2 * 3600


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
		key if str(key).startswith(("leg-", "camp:"))
		else (resolve_shipment_names([key]) or [key])[0]: value
		for key, value in (timings or {}).items()
	}


@frappe.whitelist()
def get_merge_preview(shipments, vehicle: str = None, timings=None, departure=None,
					  current_departure=None) -> dict:
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

	# ── the run as stops, which is what the sheet and the manifest are written in ──
	itinerary = build_itinerary(docs)

	# Minutes belong to the leg OUT of a stop: a row says "I am here, I leave at
	# Departure, and buffer + transit later I reach the next stop". The last stop has
	# nowhere onward, so it carries none. They are held against a representative card at
	# each stop so an edit survives the round trip through the per-card rows.
	def _leg_key(stop):
		# Keyed by the stop, not by a card: one outward card represents BOTH the camp it
		# boards at and the site it is dropped at, so keying on it made the two stops
		# share a leg and timing one silently timed the other.
		return f"leg-{stop['stop_index']}"

	def _serving_card(stop):
		serving = stop["dropping"] or stop["boarding"]
		return serving[0].name if serving else None

	# A stop's minutes come from whatever the canvas already holds for the cards it
	# serves, so re-opening the modal shows the run as it was timed instead of resetting
	# it to defaults.
	def _seeded(stop):
		held = timings.get(_leg_key(stop))
		if held:
			return held
		# A camp has no card to key its minutes on, so the canvas seeds them by the place
		# itself. Keyed by place rather than by stop index because adding a card to the
		# run renumbers the stops and the camp leg would lose what was typed against it.
		if stop["kind"] == CAMP_STOP:
			held = timings.get(f"camp:{stop['place']}")
			if held:
				return held
		for card in stop["dropping"] + stop["boarding"]:
			if card.name in timings:
				return timings[card.name]
		return None

	# Adding a card to a run that is already timed leaves only the new leg blank: half an
	# hour nobody chose sitting in the middle of an itinerary somebody did is worse than
	# an empty box asking to be filled.
	already_timed = any(_seeded(stop) for stop in itinerary[:-1])

	legs = []
	for position, stop in enumerate(itinerary):
		if position == len(itinerary) - 1:
			legs.append((0, 0))
			continue
		adjustment = _seeded(stop) or {}
		# A drive to somewhere the run collects from is not guessed at 30 minutes: AC 3.6
		# wants it stated, and a pre-filled default would let the pickup be scheduled on a
		# number nobody chose. The first leg has nothing before it to drive from.
		onward = itinerary[position + 1]
		to_a_collection = (
			onward["kind"] == SITE_STOP and onward["boarding"]
			and onward["place"] != stop["place"]
		)
		default_transit = (
			0 if (position == 0 or to_a_collection or already_timed)
			else DEFAULT_TRANSIT_MINUTES
		)
		legs.append((
			_minutes(adjustment.get("transit_minutes", default_transit)),
			_minutes(adjustment.get("buffer_minutes")),
		))

	anchor = arrival_time(docs[0]) or 0
	departure = _departure_seconds(departure)
	first_transit, first_buffer = legs[0]
	# Where the run already sits, when the canvas knows: opening the modal on a placed run
	# must show the time it actually leaves, not a time re-derived from its shift. It also
	# makes the shift the canvas applies zero until somebody changes the departure.
	current = _departure_seconds(current_departure)
	default_departure = (
		current if current is not None
		else max(0, anchor - (first_buffer + first_transit) * 60)
	)
	if departure is None:
		departure = default_departure

	walked = walk_legs(legs, anchor, departure=departure)
	peak, worst_leg, per_stop = walk_occupancy(itinerary)
	qoa_buffer = qoa_buffer_minutes()
	camp_label = next((doc.accommodation_name for doc in docs if doc.accommodation_name), None) \
		or next((doc.accommodation for doc in docs if doc.accommodation), None)

	stops = []
	for position, stop in enumerate(itinerary):
		transit, buffer_minutes = legs[position]
		departs, arrives = walked[position]
		onward = itinerary[position + 1]["place"] if position + 1 < len(itinerary) else None
		# Where the riders this stop serves are headed. At a camp that is the sites they
		# are bound for, which is not where the bus goes next once a run collects from
		# several camps before dropping anyone.
		serving = stop["boarding"] + stop["dropping"]
		shift_places = []
		for doc in serving:
			if doc.stop_location and doc.stop_location not in shift_places:
				shift_places.append(doc.stop_location)

		stops.append({
			"stop_index": stop["stop_index"],
			"kind": stop["kind"],
			"place": stop["place"],
			"stop_location": stop["place"],
			"origin_location": stop["place"],
			"next_stop_location": onward,
			"shift_location": ", ".join(shift_places) or None,
			"action": stop["action_type"],
			"action_type": stop["action_type"],
			"boarding_count": stop["boarding_count"],
			"drop_off_count": stop["drop_off_count"],
			"headcount": stop["boarding_count"] or stop["drop_off_count"],
			"boards": bool(stop["boarding"]),
			"boarding_cards": len(stop["boarding"]),
			"cards": [doc.name for doc in serving],
			# The cards this stop is the SERVING stop for - an outward card where its
			# riders are put down, a return card where they are collected. A return card
			# also appears at the home stop, where it is only being delivered, and the
			# home stop carries no minutes: letting it claim the card gave every return
			# leg 0 transit and 0 buffer. The same rule the saved row is stamped by.
			"serves": (
				[] if stop["kind"] == CAMP_STOP else
				[doc.name for doc in stop["dropping"] if own_direction(doc) != "RETURN"]
				+ [doc.name for doc in stop["boarding"]]
			) if stop["kind"] != HOME_STOP else [],
			"card_id": card_ids.get(_serving_card(stop), _serving_card(stop) or ""),
			# What the minute inputs post back: the leg belongs to the stop.
			"shipment": _leg_key(stop),
			"is_accommodation_origin": stop["kind"] == CAMP_STOP,
			"transit_minutes": transit,
			"buffer_minutes": buffer_minutes,
			"departs": _clock(departs),
			"arrives": _clock(arrives),
			"arrives_day_offset": day_offset(arrives),
			"occupancy": per_stop[position],
			"exceeded": bool(limit) and per_stop[position] > limit,
			"qoa_time": (
				_clock(departs - qoa_buffer * 60) if stop["kind"] == CAMP_STOP else None
			),
		})

	exceeded = bool(limit) and peak > limit
	alignment = _shift_alignment(docs)

	# AC 3.6: a collection the bus has to be driven to cannot be left untimed. The drive
	# INTO a stop is the previous stop's leg - minutes belong to the leg out of a row -
	# so that is the row the operator has to fill in.
	untimed = []
	for position, stop in enumerate(stops):
		if position == 0 or stop["kind"] != SITE_STOP or not stop["boarding_cards"]:
			continue
		into = stops[position - 1]
		# Only the handover drive the AC describes: dropped at Site A, collecting at
		# Site B. Arriving from the camp is the ordinary outbound leg, and a collection
		# at the place the bus is already standing is no drive at all - a stop where
		# riders both get off and get on is one stop, not two.
		if into["kind"] != SITE_STOP or into["place"] == stop["place"]:
			continue
		if not (into["transit_minutes"] or into["buffer_minutes"]):
			untimed.append(stop)
	handover_message = "" if not untimed else _(
		"Leg {0} collects at {1}. Enter the buffer and transit minutes for the drive to "
		"it before the pickup can be scheduled."
	).format(untimed[0]["stop_index"], untimed[0]["place"])

	# AC 1.5, literally now that a run is its stops: the last one is the base camp.
	ends_home = bool(itinerary) and itinerary[-1]["kind"] == HOME_STOP
	route_message = "" if ends_home else _(
		"This run does not finish at {0}. A run ends by returning to the camp it started "
		"from."
	).format(camp_label or _("the base accommodation"))

	return {
		"trip_direction": run_direction(docs),
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
		"base_accommodation": camp_label,
		"ends_at_base_camp": ends_home,
		"route_message": route_message,
		"shift_alignment": alignment,
		"handover_message": handover_message,
		# The modal disables Confirm on this alone, so it is decided here rather than
		# left to the browser to work out from the numbers.
		"can_merge": not exceeded and ends_home and not untimed,
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


def _shift_alignment(docs) -> dict:
	"""Whether the outward shift hands over to the return shift (WI-002171 AC 3.1).

	A bus can drop the incoming shift and collect the outgoing one in a single run when
	the two shifts meet: the day shift starting as the night shift ends. The AC allows
	"a couple of hours" either way, so two hours is the tolerance - the same window the
	canvas already uses to decide which runs are near enough to chain.

	Reported rather than enforced. A dispatcher merging shifts that do not quite line up
	is making an operational decision the system should show them, not refuse: the bus
	simply waits, which is what the buffer minutes are for.

	Compared circularly, so a 20:00 finish and an 08:00 start twelve hours apart are read
	as twelve hours and not as the same moment.
	"""
	outward = next((d for d in docs if own_direction(d) != "RETURN"), None)
	back = next((d for d in docs if own_direction(d) == "RETURN"), None)
	if not outward or not back:
		return {"applies": False}

	# _departure_seconds rather than _seconds_into_day: a Time column hands back a
	# timedelta, but the same field read off a plain dict is a clock string, and an
	# alignment that silently reported "no handover" for one of them would be worse than
	# useless.
	start = _departure_seconds(outward.start_time)
	end = _departure_seconds(back.end_time)
	if start is None or end is None:
		return {"applies": False}

	apart = abs(start - end)
	apart = min(apart, 86400 - apart)
	aligned = apart <= SHIFT_ALIGNMENT_TOLERANCE_SECONDS

	return {
		"applies": True,
		"outbound_shift_start": _clock(start),
		"return_shift_end": _clock(end),
		"minutes_apart": apart // 60,
		"aligned": aligned,
		"message": "" if aligned else _(
			"The outward shift starts at {0} but the return shift ends at {1} - {2} hours "
			"apart. The bus will wait between the drop-off and the pickup."
		).format(_clock(start), _clock(end), round(apart / 3600, 1)),
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
	held = frappe.db.get_value(
		"Transportation Shipment", name, ["pre_merge_trip_direction", "trip_group"], as_dict=True
	) or frappe._dict()
	if not held.pre_merge_trip_direction and not held.trip_group:
		return False

	# A same-direction run leaves no remembered direction to restore - nothing was
	# overwritten - but it still put the card in a trip group, and a card that keeps its
	# group after leaving the run is counted into a trip it is no longer part of.
	values = {"trip_group": None}
	if held.pre_merge_trip_direction:
		values["trip_direction"] = held.pre_merge_trip_direction
		values["pre_merge_trip_direction"] = None

	frappe.db.set_value("Transportation Shipment", name, values, update_modified=False)
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

# Metadata an overflow card inherits from the one it was split off. The roster moves, but
# every fact about which shift, site and camp the staff belong to is the same journey.
SPLIT_INHERITED_FIELDS = (
	"accommodation", "accommodation_name", "operations_role", "operations_shift",
	"operations_site", "project", "start_time", "end_time", "from_date", "to_date",
	"trip_direction", "routing_type_badge", "stop_location", "pair_group",
	"source_doctype", "source_docname", "requires_vehicle_retention",
	"pre_merge_trip_direction",
)


@frappe.whitelist()
def split_shipment_for_capacity(shipment: str, keep: int) -> dict:
	"""Fill a card to what the vehicle takes and move the rest to a new one (WI-002170).

	`keep` staff stay on the card being placed; everyone beyond that moves to a fresh
	Unassigned card in the pool. The roster is MOVED, not copied - every employee appears
	on exactly one of the two cards, so the two headcounts still add up to the shift and
	nobody is boarded twice.

	The overflow card keeps a link to the card it came off and to the one at the top of
	the chain, so a card split twice can still be traced back to the shift that generated
	it (AC 2.7). Its `generation_key` takes the next free `#n` suffix rather than copying
	its parent's: two records under one key would make the generator's lookup return an
	arbitrary one of them and let the pruner delete the other.
	"""
	doc = frappe.get_doc("Transportation Shipment", shipment)
	doc.check_permission("write")

	keep = cint(keep)
	roster = list(doc.transportation_shipment_employee or [])
	if keep < 1 or keep >= len(roster):
		frappe.throw(
			_("Nothing to split: this card carries {0} staff and {1} would stay on it.").format(
				len(roster), keep
			),
			title=_("Nothing to Split"),
		)

	staying, moving = roster[:keep], roster[keep:]

	overflow = frappe.new_doc("Transportation Shipment")
	for field in SPLIT_INHERITED_FIELDS:
		overflow.set(field, doc.get(field))
	overflow.status = "Unassigned"
	overflow.is_split_overflow = 1
	overflow.split_parent = doc.name
	overflow.split_root = doc.split_root or doc.name
	overflow.headcount = len(moving)
	overflow.generation_key = _next_split_key(doc.generation_key)
	for row in moving:
		overflow.append("transportation_shipment_employee", _rider_values(row))
	overflow.flags.ignore_permissions = True
	overflow.insert(ignore_permissions=True)

	doc.set("transportation_shipment_employee", [])
	for row in staying:
		doc.append("transportation_shipment_employee", _rider_values(row))
	doc.headcount = len(staying)
	doc.flags.ignore_permissions = True
	doc.save(ignore_permissions=True)

	return {
		"primary": doc.name,
		"primary_headcount": doc.headcount,
		"overflow": overflow.name,
		"overflow_headcount": overflow.headcount,
		"split_root": overflow.split_root,
	}


def _rider_values(row) -> dict:
	"""The rider fields worth carrying across a split, without the child row's identity."""
	return {
		"employee_id": row.employee_id,
		"employee_name": row.employee_name,
		"cell_number": row.cell_number,
		"accommodation": row.get("accommodation"),
		"stop_location": row.get("stop_location"),
		"operation_site": row.get("operation_site"),
	}


def _next_split_key(generation_key: str):
	"""The next free `#n` suffix on a generation key, or None when there is no key.

	An ad-hoc or Trip Request card carries no key and its overflow gets none either -
	the generator only ever looks at keyed, shift-generated records, so there is nothing
	for an unkeyed overflow to collide with.
	"""
	if not generation_key:
		return None

	base = generation_key.split("#", 1)[0]
	suffix = 2
	while frappe.db.exists("Transportation Shipment", {"generation_key": f"{base}#{suffix}"}):
		suffix += 1
	return f"{base}#{suffix}"

# ─── The run as the driver drives it ──────────────────────────────────────────
#
# A card says "these people, from this camp, to this site". That is one record but two
# things the bus does: it calls at the camp to load them and at the site to put them
# down. A run built out of cards therefore prints half its stops - the drop-offs have no
# row and no arrival time - and two cards from one camp read as two visits when the bus
# stops there once.
#
# build_itinerary turns the cards into the stops themselves: every camp the run loads at,
# every site it calls at, and the run home. That is the shape the process owner's sample
# sheet is written in, and the shape a manifest has to be printed in.

CAMP_STOP, SITE_STOP, HOME_STOP = "camp", "site", "home"


def build_itinerary(docs) -> list:
	"""The physical stops one run makes, in order, from the cards it carries.

	Camps first: the bus collects everyone before it starts putting them down, and one
	camp is one visit however many cards board there. Then the sites in the order the
	cards are due, with a site the run calls at twice in a row collapsed into the single
	visit it is - a place where riders both get off and get on is one stop, not two.
	Finally the run home, which no card describes because a card's journey ends when its
	own riders do.
	"""
	stops = []

	# ── the camps, in the order the run first needs them ──
	camps = []
	for doc in docs:
		if own_direction(doc) == "RETURN":
			continue
		if doc.accommodation and doc.accommodation not in camps:
			camps.append(doc.accommodation)

	for accommodation in camps:
		loading = [
			doc for doc in docs
			if doc.accommodation == accommodation and own_direction(doc) != "RETURN"
		]
		stops.append(_stop(CAMP_STOP, _camp_place(loading[0]), boarding=loading))

	# ── the sites, in the order the cards are due ──
	for doc in docs:
		boards = own_direction(doc) == "RETURN"
		place = doc.stop_location
		last = stops[-1] if stops else None
		if last and last["kind"] == SITE_STOP and last["place"] == place:
			# The same visit: riders from another card leaving here too, or the handover
			# where one load gets off and the next gets on.
			(last["boarding"] if boards else last["dropping"]).append(doc)
			_recount(last)
			continue
		stops.append(
			_stop(SITE_STOP, place, boarding=[doc] if boards else [], dropping=[] if boards else [doc])
		)

	# ── and home ──
	going_home = [doc for doc in docs if own_direction(doc) == "RETURN"]
	base = next((doc for doc in docs if doc.accommodation), None)
	if base:
		stops.append(_stop(HOME_STOP, _camp_place(base), dropping=going_home))

	for index, stop in enumerate(stops, start=1):
		stop["stop_index"] = index
	return stops


def _stop(kind, place, boarding=None, dropping=None) -> dict:
	stop = {
		"kind": kind,
		"place": place,
		"boarding": list(boarding or []),
		"dropping": list(dropping or []),
	}
	_recount(stop)
	return stop


def _recount(stop) -> None:
	stop["boarding_count"] = sum(cint(doc.headcount) for doc in stop["boarding"])
	stop["drop_off_count"] = sum(cint(doc.headcount) for doc in stop["dropping"])
	if stop["boarding"] and stop["dropping"]:
		stop["action_type"] = "Combined"
	elif stop["boarding"]:
		stop["action_type"] = "Boarding"
	else:
		stop["action_type"] = "Dropping Off"


def _camp_place(doc):
	"""The Location that stands for a card's camp, falling back to its readable name."""
	return _camp_stop(doc) or doc.accommodation_name or doc.accommodation


def walk_occupancy(stops) -> tuple:
	"""Running load after each stop, and the peak, walked drop-off first.

	The seats a load vacates are what the next load boards into, so a stop where both
	happen is measured in that order - adding first reports an overload that never
	happens. One walk, used by the modal, by the saved rows and by the Route Plan's own
	capacity check, so none of them can disagree about how full the bus gets.
	"""
	onboard, peak, worst, per_stop = 0, 0, 1, []
	for stop in stops:
		onboard -= cint(stop.get("drop_off_count"))
		onboard += cint(stop.get("boarding_count"))
		per_stop.append(onboard)
		if onboard > peak:
			peak, worst = onboard, stop.get("stop_index") or len(per_stop)
	return peak, worst, per_stop
