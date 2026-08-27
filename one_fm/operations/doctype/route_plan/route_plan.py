# Copyright (c) 2026, oneaborance and contributors
# For license information, please see license.txt

import datetime

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, getdate, now_datetime, to_timedelta
from frappe.model.document import Document

# Open-ended sentinels: a shipment missing a bound is treated as always-active on
# that edge (a standing card with no date range / a whole-day time window).
_DATE_MIN = datetime.date.min
_DATE_MAX = datetime.date.max
_TIME_START = datetime.timedelta(0)
_TIME_END = datetime.timedelta(days=1)

# The direction a merged trip carries once cards are combined (WI-002071).
MIXED_DIRECTION = "MIXED"


class RoutePlan(Document):
	def validate(self):
		self._validate_dates()
		self._validate_single_active()
		self._validate_single_default()
		self._validate_vehicle_retention_locks()
		self._validate_vehicle_datetime_locks()
		self._validate_trip_group_single_vehicle()
		self._validate_vehicle_capacity()

	def _validate_dates(self):
		"""Ensure effective_until >= effective_from when set."""
		if self.effective_until and self.effective_from:
			if self.effective_until < self.effective_from:
				frappe.throw(_("Effective Until must be on or after Effective From"))

	def _validate_single_active(self):
		"""Only one Route Plan can be Active at a time."""
		if self.status == "Active":
			existing = frappe.db.get_value(
				"Route Plan",
				{"status": "Active", "name": ["!=", self.name]},
				"name"
			)
			if existing:
				frappe.throw(
					_("Route Plan {0} is already Active. Deactivate it first or set it to Expired.").format(existing)
				)

	def _validate_single_default(self):
		"""Only one Route Plan can be marked as Default."""
		if cint(self.is_default):
			existing = frappe.db.get_value(
				"Route Plan",
				{"is_default": 1, "name": ["!=", self.name]},
				"name"
			)
			if existing:
				frappe.throw(
					_("A default Route Plan already exists ({0}). Only one plan can be set as default at a time.").format(existing)
				)

	def _validate_vehicle_retention_locks(self):
		"""Block a vehicle whose timeline is held by a retention (STANDBY) shipment.

		A shipment flagged ``requires_vehicle_retention`` keeps its bus parked at
		the site for the whole trip, so no other trip may share that vehicle while
		the retention window is live (TR4-7). For every vehicle assigned on this
		plan we compare each retention-locked shipment against every other shipment
		on the same vehicle and reject the save when their calendar ranges
		(from_date..to_date) and daily time windows (start_time..end_time) both
		overlap. Scope is this plan's own assignments — the canvas keeps all drops
		in one active/default plan.
		"""
		# Group the distinct shipments assigned to each vehicle on this plan. The
		# same shipment can appear on two rows (Outward + Return); a set collapses
		# those so a card never conflicts with itself.
		vehicle_shipments = {}
		shipment_names = set()
		for row in self.assignments:
			if not row.vehicle or not row.transportation_shipment:
				continue
			vehicle_shipments.setdefault(row.vehicle, set()).add(row.transportation_shipment)
			shipment_names.add(row.transportation_shipment)

		if not shipment_names:
			return

		shipment_map = self._get_shipment_windows(shipment_names)

		for vehicle, names in vehicle_shipments.items():
			conflict = _detect_retention_conflict(names, shipment_map)
			if conflict:
				self._throw_retention_lock(vehicle, conflict)

	def _validate_vehicle_datetime_locks(self):
		"""Full-span vehicle block-out for multi-day lock windows (TR-8).

		The assignment ``start_time``/``end_time`` are ISO timestamps whose DATE
		part encodes the multi-day lock lifespan and whose TIME part is the daily
		trip window. A row whose lock spans more than a single day (its end date
		is later than its start date) reserves the vehicle across every calendar
		day in that span, so no other shipment's run may share the vehicle while
		the lock is live (the operational example: a bus retained across all six
		calendar days).

		For every vehicle we compare each multi-day lock against every other row
		and reject the save when their date ranges overlap. Rows of the same
		shipment (Outward + Return) and stops chained into the same trip are
		exempt, and a lock whose last day has already passed is ignored so an
		expired reservation frees the vehicle automatically. Scope is this plan's
		own assignments — the canvas keeps every drop in one active/default plan,
		mirroring the retention lock above.
		"""
		by_vehicle = {}
		for row in self.assignments:
			if row.vehicle:
				by_vehicle.setdefault(row.vehicle, []).append(row)

		today = getdate(now_datetime())

		for vehicle, rows in by_vehicle.items():
			# Only a multi-day lock blocks the whole vehicle; single-day runs keep
			# the normal time-overlap rules (client-side + retention lock).
			lock_rows = [r for r in rows if _is_multiday_lock(r)]
			if not lock_rows:
				continue

			for lock in lock_rows:
				lock_from, lock_to = _row_date_range(lock)

				# Skip a lock whose last day has passed — the vehicle is free again.
				if lock_to and lock_to < today:
					continue

				for other in rows:
					if other is lock:
						continue
					# Same shipment (OUT + RET) or same chained trip never conflict.
					if (
						other.transportation_shipment
						and other.transportation_shipment == lock.transportation_shipment
					):
						continue
					if other.trip_group and other.trip_group == lock.trip_group:
						continue

					other_from, other_to = _row_date_range(other)
					if _date_ranges_overlap(lock_from, lock_to, other_from, other_to):
						self._throw_datetime_lock(vehicle, lock)

	def _throw_datetime_lock(self, vehicle, lock):
		"""Raise the block-out error for an overlapping multi-day lock window."""
		trip_label = lock.transportation_shipment or lock.card_id or _("a multi-day run")
		lock_from, lock_to = _row_date_range(lock)
		start = _format_lock_date(lock_from) or _("today")
		end = _format_lock_date(lock_to) or _("ongoing")
		frappe.throw(
			_(
				"Vehicle Assignment Error: {0} is locked from {1} to {2} for {3} and "
				"cannot be assigned to an overlapping run."
			).format(vehicle, start, end, trip_label),
			title=_("Vehicle Assignment Error"),
		)

	def _get_shipment_windows(self, shipment_names) -> dict:
		"""Return {name: retention window dict} for the given shipments."""
		from frappe.query_builder import DocType

		TransportationShipment = DocType("Transportation Shipment")
		rows = (
			frappe.qb.from_(TransportationShipment)
			.select(
				TransportationShipment.name,
				TransportationShipment.requires_vehicle_retention,
				TransportationShipment.from_date,
				TransportationShipment.to_date,
				TransportationShipment.start_time,
				TransportationShipment.end_time,
				TransportationShipment.source_docname,
			)
			.where(TransportationShipment.name.isin(list(shipment_names)))
		).run(as_dict=True)
		return {row.name: row for row in rows}

	def _throw_retention_lock(self, vehicle, lock):
		"""Raise the strict STANDBY validation error for a retention conflict."""
		# The locking trip is named by its source Trip Request; fall back to the
		# shipment name when the card has no source reference.
		trip_label = lock.source_docname or lock.name
		until = _format_lock_until(lock.end_time)
		until_clause = _(" until {0}").format(until) if until else ""
		frappe.throw(
			_("Vehicle Assignment Error: {0} is locked on STANDBY for {1}{2}.").format(
				vehicle, trip_label, until_clause
			),
			title=_("Vehicle Assignment Error"),
		)

	def _validate_trip_group_single_vehicle(self):
		"""A journey leg lives on exactly one vehicle (MA4-13 AC1/AC2).

		Every accommodation stop merged into one bus run shares the same
		``trip_group`` hash, and each direction of that run is one physical
		vehicle. Reassigning the vehicle on the scheduling board cascades to
		every stop of the leg (handled on the canvas), so a saved plan must never
		have one ``(trip_group, direction)`` split across vehicles. Outbound and
		return legs keep their own vehicle (Multi-Day Lane Replication), so the
		direction is part of the key. Reject the save when a leg is split, naming
		the journey so the dispatcher can re-drop it cleanly.
		"""
		leg_vehicle = {}
		for row in self.assignments:
			if not row.trip_group or not row.vehicle:
				continue
			key = (row.trip_group, _row_direction(row))
			existing = leg_vehicle.get(key)
			if existing and existing != row.vehicle:
				trip_label = row.trip_name or row.trip_group
				frappe.throw(
					_(
						"Trip Assignment Error: the stops of {0} are split across "
						"vehicles ({1} and {2}). A journey must run on a single "
						"vehicle — reassign the whole trip together."
					).format(trip_label, existing, row.vehicle),
					title=_("Trip Assignment Error"),
				)
			leg_vehicle.setdefault(key, row.vehicle)

	def _validate_vehicle_capacity(self):
		"""Hold each trip, and each set of concurrent trips, to the bus seats.

		A vehicle that finishes a 05:10 drop is free to run again at 07:00, so a
		lane is not one pooled load — it is a series of time-bounded trips
		(WI-002000). Two levels are enforced against the same limit:

		* **Each trip on its own** — the accommodation cards merged onto one
		  ``(vehicle, trip_group)`` ride together even though their stops are
		  sequential, so their headcounts still sum (MA4-13) — unless the run
		  both drops off and picks up, which is walked leg by leg.
		* **Trips that run at the same time** — when two trips' windows overlap,
		  their passengers are on the bus together and the totals add up.

		Trips whose windows do not overlap never see each other's passengers, which
		is what stops a finished earlier run from blocking the next assignment.

		The limit is the vehicle's own ``Max Passenger Capacity``: whether its seat
		count includes the driver is a per-vehicle answer, so the fleet record
		decides, not this code.
		"""
		trips = self._logical_trips()
		if not trips:
			return

		limits = _passenger_limits({trip.vehicle for trip in trips})

		by_vehicle = {}
		for trip in trips:
			by_vehicle.setdefault(trip.vehicle, []).append(trip)

		for vehicle, vehicle_trips in by_vehicle.items():
			limit = limits.get(vehicle)
			if not limit:
				# Vehicle master has no seat count configured — nothing to enforce.
				continue

			# One trip over the limit on its own is reported as the overloaded run
			# it is, naming the seat shortfall (MA4-13). Ordered so the reported
			# trip is stable across saves.
			for trip in sorted(vehicle_trips, key=lambda t: t.key):
				if trip.direction == MIXED_DIRECTION:
					# A merged trip boards and alights along the way, so its stops do
					# not all ride together and summing them would refuse a load the
					# bus can actually carry (WI-002071).
					self._validate_mixed_trip_legs(trip, limit)
				elif trip.headcount > limit:
					self._throw_capacity_exceeded(vehicle, trip.direction, trip.headcount, limit)

			concurrent = _peak_concurrent_headcount(vehicle_trips)
			if concurrent > limit:
				frappe.throw(
					_(
						"Capacity Exceeded: Total overlapping passengers ({0}) exceeds "
						"vehicle limit ({1})."
					).format(concurrent, limit),
					title=_("{0}: Vehicle Capacity Exceeded").format(vehicle),
				)

	def _logical_trips(self) -> list:
		"""Collapse the assignment rows into the trips a vehicle actually runs.

		Rows sharing a ``(vehicle, trip_group)`` are the stops of one run: their
		headcounts sum and the trip spans from its first stop's start to its last
		stop's end. A run whose stops do not all travel the same way is a mixed one
		and is measured leg by leg instead. A row with no ``trip_group`` is a
		standalone drop and becomes a trip of its own, so it is weighed like any other.

		Each trip carries the daily time window its stops cover and the calendar
		lifespan they are live for — the two halves of the timestamps a Route Plan
		Assignment stores (TR-8: date part = multi-day lock, time part = the daily
		run).
		"""
		trips = {}
		for idx, row in enumerate(self.assignments):
			if not row.vehicle:
				continue
			direction = _row_direction(row)
			# Standalone rows are keyed by position so two of them never merge.
			group = row.trip_group or f"\0row-{idx}"
			# One trip group on one vehicle is one bus run, whichever way its stops
			# travel. Keying the direction in as well split a chained run - an outward
			# drop and the return pickup made at the same stop - into two pseudo-trips
			# whose windows overlap each other, so the concurrency check added the same
			# bus to itself and refused a load it was already carrying (WI-002160).
			key = (row.vehicle, group)
			start, end = _row_time_window(row)
			live_from, live_to = _row_date_range(row)

			trip = trips.get(key)
			if not trip:
				trips[key] = frappe._dict(
					key=key,
					vehicle=row.vehicle,
					direction=direction,
					headcount=cint(row.headcount),
					start=start,
					end=end,
					live_from=live_from,
					live_to=live_to,
					# Kept so a merged trip can be walked stop by stop (WI-002071);
					# the summed headcount above is meaningless for one.
					rows=[row],
				)
				continue

			trip.rows.append(row)
			# Stops that do not all travel the same way make this a mixed run, walked leg
			# by leg instead of summed. The row's own ``direction`` only ever said MIXED
			# when the Merge Trip modal wrote it back; chaining a return stop onto an
			# outbound trip left every row on its original heading (WI-002160).
			if direction != trip.direction:
				trip.direction = MIXED_DIRECTION
			trip.headcount += cint(row.headcount)
			trip.start = min(trip.start, start)
			trip.end = max(trip.end, end)
			trip.live_from = min(filter(None, [trip.live_from, live_from]), default=None)
			trip.live_to = max(filter(None, [trip.live_to, live_to]), default=None)

		# How full the bus gets is not the same as how many the trip carries once a trip
		# can be merged, and it is the occupancy that everything downstream compares
		# against the seats.
		runs = list(trips.values())
		for trip in runs:
			trip.occupancy, trip.worst_leg = _trip_peak(trip)

		return runs

	def _validate_mixed_trip_legs(self, trip, limit):
		"""Hold every leg of a merged trip to the seat count (WI-002071).

		A Mixed trip is one vehicle run that both drops off and picks up, so its stops
		do not all ride together: workers dropped at Stop 1 are off the bus before the
		Stop 2 boarders get on. Summing the stops - which is right for a single-direction
		trip, where every card's riders are aboard at once - would refuse a load the bus
		can carry.

		Occupancy is walked stop by stop instead. Each row's own shipment says which way
		its riders travel: an Outward card's riders board at the camp and leave at that
		card's stop, a Return card's riders join at that card's stop and stay aboard to
		the camp. So the bus leaves the camp carrying every Outward rider, and each stop
		in turn sheds its Outward riders and takes on its Return ones.

		Disembarking is applied before boarding at each stop, per the third criterion: at
		a stop where both happen the seats being vacated are available to the people
		getting on, and adding first would report an overload that never occurs.

		The peak across the legs is what has to fit, not the total that ever rode.
		"""
		peak, worst_leg = _trip_peak(trip)

		if peak > limit:
			frappe.throw(
				_(
					"Capacity Exceeded on leg {0}: {1} passengers against a vehicle limit "
					"of {2}. A merged trip is measured leg by leg, so this is the busiest "
					"point of the run rather than everyone it carries in total."
				).format(worst_leg, peak, limit),
				title=_("{0}: Vehicle Capacity Exceeded").format(trip.vehicle),
			)

	def _throw_capacity_exceeded(self, vehicle, direction, total_passengers, limit):
		"""Raise the overloading block with the exact seat shortfall (MA4-13 AC4)."""
		dir_label = _("return") if direction == "RETURN" else _("outbound")
		frappe.throw(
			_(
				"Capacity Exceeded: the {0} run on {1} carries {2} passengers but the "
				"vehicle takes {3}. You are short {4} seat(s) — assign a larger bus or "
				"arrange a taxi."
			).format(dir_label, vehicle, total_passengers, limit, total_passengers - limit),
			title=_("Vehicle Capacity Exceeded"),
		)

	def before_save(self):
		self.last_modified_by_user = frappe.session.user
		self.last_modified_at = frappe.utils.now()


def _row_direction(row) -> str:
	"""Normalize an assignment row's direction to OUTBOUND/RETURN/MIXED.

	The Route Plan Assignment ``direction`` Select stores OUTBOUND/RETURN/MIXED, but a
	blank or stray value is collapsed to OUTBOUND so a leg is never silently
	dropped from a capacity or single-vehicle cluster.

	MIXED has to be recognised, not defaulted: answering "not a return, so outbound"
	keyed a merged trip as an outbound one, and its stops were then summed as if they
	all rode together instead of being walked leg by leg.
	"""
	return _normalize_shipment_direction(row.direction)


def _detect_retention_conflict(shipment_names, shipment_map):
	"""Return the locking retention shipment that a co-assigned trip overlaps.

	Given the distinct shipments on one vehicle, find any retention-locked
	shipment whose window overlaps another shipment on the same vehicle and
	return that lock (a dict). Returns ``None`` when the vehicle is clear.
	Iteration is sorted so the reported conflict is stable across saves.
	"""
	ordered = sorted(shipment_names)
	retention = [
		shipment_map[name]
		for name in ordered
		if shipment_map.get(name) and cint(shipment_map[name].requires_vehicle_retention)
	]
	if not retention:
		return None

	for lock in retention:
		for other_name in ordered:
			if other_name == lock.name:
				continue
			other = shipment_map.get(other_name)
			if other and _windows_overlap(lock, other):
				return lock
	return None


def _windows_overlap(a, b) -> bool:
	"""True when two shipments overlap on both calendar range and daily time."""
	if not _date_ranges_overlap(a.from_date, a.to_date, b.from_date, b.to_date):
		return False
	return _time_windows_overlap(a.start_time, a.end_time, b.start_time, b.end_time)


def _date_ranges_overlap(a_from, a_to, b_from, b_to) -> bool:
	"""Inclusive overlap of two calendar ranges; missing bounds are open-ended."""
	a_from = getdate(a_from) if a_from else _DATE_MIN
	a_to = getdate(a_to) if a_to else _DATE_MAX
	b_from = getdate(b_from) if b_from else _DATE_MIN
	b_to = getdate(b_to) if b_to else _DATE_MAX
	return a_from <= b_to and b_from <= a_to


def _time_windows_overlap(a_start, a_end, b_start, b_end) -> bool:
	"""Strict overlap of two daily time windows; missing edges span the whole day.

	Windows that merely touch (one ends exactly when the other starts) do not
	overlap, so a return leg can begin at the instant a retention lock releases.
	"""
	a_start = to_timedelta(a_start) if a_start else _TIME_START
	a_end = to_timedelta(a_end) if a_end else _TIME_END
	b_start = to_timedelta(b_start) if b_start else _TIME_START
	b_end = to_timedelta(b_end) if b_end else _TIME_END
	return a_start < b_end and b_start < a_end


_DAY_SECONDS = 24 * 60 * 60


def _passenger_limits(vehicle_names) -> dict:
	"""``{vehicle: passengers it may carry}`` for the vehicles on a plan.

	The stored ``custom_max_passenger_capacity`` is what the Vehicle form shows,
	so it is what the dispatcher is held to. It is derived on every Vehicle save
	and backfilled by patch, but a record that has somehow never been through
	either would read 0 and wave everything through — so the same formula is
	applied on the spot instead (WI-002000).
	"""
	from one_fm.overrides.vehicle import passenger_capacity

	limits = {}
	for vehicle in frappe.get_all(
		"Vehicle",
		filters={"name": ["in", list(vehicle_names)]},
		fields=["name", "seats", "custom_includes_driver_seat", "custom_max_passenger_capacity"],
	):
		limits[vehicle.name] = cint(vehicle.custom_max_passenger_capacity) or passenger_capacity(
			vehicle.seats, vehicle.custom_includes_driver_seat
		)
	return limits


def _iso_time_of_day(value):
	"""Seconds past midnight of a timeline stamp (``2026-07-20T06:00:00Z``).

	Only the clock time is taken: the date half of these stamps is the multi-day
	lock lifespan (TR-8), so a run that repeats daily has to be compared by the
	hour it leaves, not the day it was first placed.
	"""
	if not value:
		return None
	text = str(value).replace("T", " ").replace("Z", "").strip()
	try:
		moment = get_datetime(text)
	except Exception:
		return None
	return moment.hour * 3600 + moment.minute * 60 + moment.second


def _row_time_window(row):
	"""The daily window a row occupies, as seconds past midnight.

	A row with no times spans the whole day, so it is never mistaken for a run
	that has already finished. An end at or before the start is a run over
	midnight (22:00 -> 01:00) and is carried past the day boundary rather than
	being read as a zero-length block.
	"""
	start = _iso_time_of_day(row.start_time)
	end = _iso_time_of_day(row.end_time)

	if start is None and end is None:
		return 0, _DAY_SECONDS
	if start is None:
		start = 0
	if end is None:
		end = _DAY_SECONDS
	if end <= start:
		end += _DAY_SECONDS
	return start, end


def _trips_share_the_road(a, b) -> bool:
	"""True when two trips put passengers on the same bus at the same moment.

	Both halves have to meet: the trips must be live on overlapping calendar
	dates, and their daily windows must overlap. Windows that merely touch — one
	ending exactly as the next begins — do not, so a bus can turn straight around.
	Comparison is circular over the day so a run past midnight still meets an
	early-morning one.

	The two directions of one journey are the exception: they are the same bus
	going out and coming back, never both at once, so they are never added
	together however their windows are recorded (MA4-13, and the same exemption
	the multi-day lock check makes).
	"""
	same_journey = a.key[1] == b.key[1]
	if same_journey and a.direction != b.direction:
		return False

	if not _date_ranges_overlap(a.live_from, a.live_to, b.live_from, b.live_to):
		return False

	for shift in (-_DAY_SECONDS, 0, _DAY_SECONDS):
		if a.start < b.end + shift and b.start + shift < a.end:
			return True
	return False


def _peak_concurrent_headcount(trips) -> int:
	"""The most passengers these trips ever have on the bus at once.

	Each trip in turn is taken as the anchor and everything overlapping it is
	added, which is what "total overlapping passengers" means from the point of
	view of the trip being assigned.

	ponytail: O(n^2) and anchored rather than a true sweep, so a chain where A
	meets B and A meets C but B and C never meet is counted as all three. A lane
	holds a handful of trips a day; swap in a sweep line if that ever changes.
	"""
	peak = 0
	for anchor in trips:
		total = _trip_occupancy(anchor) + sum(
			_trip_occupancy(other)
			for other in trips
			if other is not anchor and _trips_share_the_road(anchor, other)
		)
		peak = max(peak, total)
	return peak


def _trip_occupancy(trip) -> int:
	"""The most passengers one trip ever has aboard.

	For a single-direction trip that is its headcount - every card's riders are on the
	bus together. For a merged trip it is the busiest leg, because its stops are not all
	aboard at once and the sum is a total the bus never carries (WI-002071).
	"""
	return cint(trip.occupancy if trip.get("occupancy") is not None else trip.headcount)


def _trip_peak(trip):
	"""(peak occupancy, busiest stop) for one logical trip, walked as physical stops.

	A card is "these people, from this camp, to this site" - one record, but two things
	the bus does. Walking the cards assumes everyone is aboard from the moment the run
	starts, which over-reports the moment a run drops one load before calling at a later
	camp for the next. Walking the STOPS is what actually happens, and it is the same
	walk the trip modal shows the operator: the two must not be able to disagree about
	whether a run fits, or the modal accepts a merge the save then refuses.

	Falls back to the card walk when the rows carry no shipments to build stops from - a
	hand-made row still has a headcount and a direction worth counting.
	"""
	from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
		build_itinerary,
		walk_occupancy,
	)

	by_index = sorted(
		trip.rows,
		key=lambda row: (cint(row.stop_index), str(row.start_time or ""), row.name or ""),
	)
	names = [row.transportation_shipment for row in by_index if row.transportation_shipment]
	if names:
		cards = _cards_for_itinerary(by_index)
		if cards:
			peak, worst, _per_stop = walk_occupancy(build_itinerary(cards))
			return peak, worst

	if trip.direction != MIXED_DIRECTION:
		return cint(trip.headcount), 1

	directions = _shipment_directions(names)
	stops = [
		{
			"headcount": cint(row.headcount),
			"boards": (directions.get(row.transportation_shipment) or _row_direction(row))
			== "RETURN",
		}
		for row in by_index
	]
	peak, worst_leg, _legs = leg_occupancy(stops)
	return peak, worst_leg


def _cards_for_itinerary(rows) -> list:
	"""The rows as card-shaped records build_itinerary can read, in run order.

	Each row's headcount is used rather than the shipment's: the row is what this plan
	actually carries, and a card can be split across vehicles.
	"""
	names = [row.transportation_shipment for row in rows if row.transportation_shipment]
	if not names:
		return []

	facts = {
		doc.name: doc
		for doc in frappe.get_all(
			"Transportation Shipment",
			filters={"name": ["in", list(set(names))]},
			fields=["name", "accommodation", "accommodation_name", "stop_location",
					"trip_direction", "pre_merge_trip_direction", "start_time", "end_time"],
		)
	}

	cards = []
	for row in rows:
		fact = facts.get(row.transportation_shipment)
		if not fact:
			continue
		cards.append(frappe._dict({
			"name": fact.name,
			"accommodation": fact.accommodation,
			"accommodation_name": fact.accommodation_name,
			"stop_location": fact.stop_location or row.stop_location,
			"headcount": cint(row.headcount),
			"trip_direction": fact.trip_direction,
			"pre_merge_trip_direction": fact.pre_merge_trip_direction,
			"start_time": fact.start_time,
			"end_time": fact.end_time,
		}))

	# Ordered the way the bus reaches them, which is how the trip modal orders the same
	# cards. Sorting on the stored stop_index instead let the two build different runs
	# out of the same cards and reach different peaks - the modal would accept a merge
	# the save then refused.
	from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
		arrival_order,
	)

	cards.sort(key=arrival_order)
	return cards


def _iso_to_date(value):
	"""Return the calendar date of a timeline ISO stamp (``2026-07-20T06:00:00Z``)."""
	if not value:
		return None
	text = str(value).replace("T", " ").replace("Z", "").strip()
	try:
		return getdate(get_datetime(text))
	except Exception:
		return None


def _row_date_range(row):
	"""Return the (from_date, to_date) lock lifespan encoded in a row's timestamps."""
	return _iso_to_date(row.start_time), _iso_to_date(row.end_time)


def _is_multiday_lock(row) -> bool:
	"""True when a row's lock lifespan spans more than one calendar day.

	Single-day runs (start date == end date) are ordinary trips and never
	block the whole vehicle; only a genuine multi-day span acts as a full
	block-out reservation.
	"""
	start, end = _row_date_range(row)
	return bool(start and end and end > start)


def _format_lock_date(value) -> str:
	"""Render a date as ``15-07-2026`` for lock error messages."""
	if not value:
		return ""
	return getdate(value).strftime("%d-%m-%Y")


def _format_lock_until(end_time) -> str:
	"""Render a Time value as a 12-hour clock label, e.g. ``02:00 PM``."""
	if not end_time:
		return ""
	total = int(to_timedelta(end_time).total_seconds())
	hours = (total // 3600) % 24
	minutes = (total % 3600) // 60
	return datetime.time(hours, minutes).strftime("%I:%M %p")


def _shipment_directions(shipment_names) -> dict:
	"""{shipment: OUTBOUND|RETURN} for the cards on a merged trip.

	Which way a card's own riders travel is what the leg walk needs: an Outward card's
	riders are aboard from the camp and leave at its stop, a Return card's join there.
	Neither the assignment row nor the shipment's live ``trip_direction`` can answer
	that any more - merging overwrites both with MIXED. ``pre_merge_trip_direction``,
	written by the merge and restored when a card leaves one, is the surviving record
	of the journey the card was generated for, so it is read first.

	A merged card with no record falls back to OUTBOUND, which is the conservative
	answer: it counts those riders as aboard from the camp, so the walk over-reports
	rather than passing a run the bus cannot carry.
	"""
	names = [name for name in shipment_names if name]
	if not names:
		return {}

	return {
		row.name: _card_direction(row.trip_direction, row.pre_merge_trip_direction)
		for row in frappe.get_all(
			"Transportation Shipment",
			filters={"name": ["in", list(set(names))]},
			fields=["name", "trip_direction", "pre_merge_trip_direction"],
		)
	}


def _card_direction(trip_direction, pre_merge_trip_direction) -> str:
	"""The way one card's own riders travel, as OUTBOUND or RETURN."""
	flag = _normalize_shipment_direction(trip_direction)
	if flag != MIXED_DIRECTION:
		return flag
	return _normalize_shipment_direction(pre_merge_trip_direction)


def _normalize_shipment_direction(value: str) -> str:
	"""Shipment vocabulary (Outward/Return/Mixed) as an assignment-side flag."""
	flag = (value or "").strip().upper()
	if flag.startswith("MIX"):
		return MIXED_DIRECTION
	return "RETURN" if flag.startswith("RET") else "OUTBOUND"


def leg_occupancy(stops):
	"""Walk a merged trip stop by stop and report how full the bus gets.

	`stops` is the run in order, each entry carrying a headcount and whether those
	riders board there (True) or leave there (False). Returns
	(peak, worst_leg, per_leg_occupancy).

	Shared by the Route Plan validation and the canvas merge preview (WI-002078), so the
	number the modal shows an operator before they confirm is the same number the save
	will judge them by. Two implementations of this would drift, and the operator would
	be told a merge is fine and then refused.

	Disembarking is applied before boarding at each stop: at a stop where both happen the
	seats being vacated are available to the people getting on, and adding first reports
	an overload that never occurs.
	"""
	# Everyone the trip carries out of the camp is aboard before the first stop.
	occupancy = sum(stop["headcount"] for stop in stops if not stop["boards"])
	peak = occupancy
	worst_leg = 1
	per_leg = []

	for leg, stop in enumerate(stops, start=1):
		if stop["boards"]:
			occupancy += stop["headcount"]
		else:
			occupancy -= stop["headcount"]

		per_leg.append(occupancy)
		if occupancy > peak:
			peak, worst_leg = occupancy, leg

	return peak, worst_leg, per_leg
