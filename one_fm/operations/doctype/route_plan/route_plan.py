# Copyright (c) 2026, oneaborance and contributors
# For license information, please see license.txt

import datetime
import re

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

# The direction a merged trip carries once cards are combined.
MIXED_DIRECTION = "MIXED"

# A trip name as the canvas mints it: an optional leased "S-" prefix, the vehicle's own
# number, then a two-digit sequence. "S-106" is vehicle 1 run 06; "S-1303" is vehicle 13
# run 03; "1901" is vehicle 19 run 01 on a bus that is not leased.
TRIP_NAME = re.compile(r"^(S-)?(\d+?)(\d{2})$")


class RoutePlan(Document):
	def validate(self):
		self._validate_dates()
		self._validate_single_active()
		self._validate_single_default()

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

	def before_save(self):
		self.last_modified_by_user = frappe.session.user
		self.last_modified_at = frappe.utils.now()

	def on_trash(self):
		# The assignments are the plan's own; without this the link to them refuses the delete.
		frappe.db.delete("Route Plan Assignment", {"route_plan": self.name})


def plan_row_fields() -> list:
	"""Every data column of a Route Plan Assignment, plus name, idx and modified."""
	from frappe.model import no_value_fields

	return ["name", "idx", "modified"] + [
		df.fieldname
		for df in frappe.get_meta("Route Plan Assignment").fields
		if df.fieldtype not in no_value_fields
	]


def get_plan_rows(plan, vehicles=None, trip_groups=None, fields=None, for_update=False) -> list:
	"""The assignments of one plan as frappe._dict rows, in the order the plan lists them.

	idx is the order the rows had as a child table, which is the order every reader of a
	run relies on; creation breaks a tie between records written in the same save.
	``vehicles`` / ``trip_groups`` narrow the read, and ``for_update`` locks what it reads
	until the transaction ends.
	"""
	filters = {"route_plan": plan}
	if vehicles is not None:
		filters["vehicle"] = ["in", list(vehicles) or [""]]
	if trip_groups is not None:
		filters["trip_group"] = ["in", list(trip_groups) or [""]]
	return frappe.db.get_values(
		"Route Plan Assignment",
		filters,
		fields or plan_row_fields(),
		as_dict=True,
		order_by="idx asc, creation asc",
		for_update=for_update,
	)


class PlanRules:
	"""The plan-wide rules, judged over a set of Route Plan Assignment rows.

	``rows`` is the plan as this save would leave it, ``before`` the same rows as they are
	stored (None for a plan that has none yet). Every rule groups rows by vehicle except
	the trip-group rule, which compares one trip group across vehicles, so a caller may
	pass only the vehicles it touches plus the vehicles holding its trip groups.
	"""

	def __init__(self, rows, before=None):
		self.rows = rows
		self.before = before

	def run(self):
		"""The rules in the order the Route Plan save used to run them."""
		self._validate_vehicle_retention_locks()
		self._validate_vehicle_datetime_locks()
		self._validate_trip_group_single_vehicle()
		self._rename_duplicate_trip_names()
		self._validate_vehicle_capacity()

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
		for row in card_rows(self.rows):
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
		for row in card_rows(self.rows):
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
		for row in card_rows(self.rows):
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
. Two levels are enforced against the same limit:

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
		untouched = self._vehicles_this_save_did_not_touch(trips)
		untouched_trips = self._trips_this_save_did_not_touch(trips)

		by_vehicle = {}
		for trip in trips:
			by_vehicle.setdefault(trip.vehicle, []).append(trip)

		for vehicle, vehicle_trips in by_vehicle.items():
			limit = limits.get(vehicle)
			if not limit:
				# Vehicle master has no seat count configured — nothing to enforce.
				continue

			if vehicle in untouched:
				# Nothing was dropped on or taken off this bus in this save, so whatever
				# it carries it was already carrying and the plan was saved that way. A
				# roster that has grown since is a real overload, but it is this bus's
				# problem and the board colours the lane for it - refusing every other
				# edit on the plan until someone fixes it blocks the wrong person.
				continue

			# One trip over the limit on its own is reported as the overloaded run
			# it is, naming the seat shortfall (MA4-13). Ordered so the reported
			# trip is stable across saves.
			for trip in sorted(vehicle_trips, key=lambda t: t.key):
				if (vehicle, trip.key) in untouched_trips:
					# This run is exactly as it was saved. Whatever it carries, this save
					# neither caused it nor can fix it, and refusing the edit in front of
					# the dispatcher blocks the wrong person. The lane still colours it.
					continue
				if trip.direction == MIXED_DIRECTION:
					# A merged trip boards and alights along the way, so its stops do
					# not all ride together and summing them would refuse a load the
					# bus can actually carry.
					self._validate_mixed_trip_legs(trip, limit)
				elif trip.occupancy > limit:
					# Judged and quoted on the peak onboard load, not the sum of every
					# stop's riders. A one-way run reads the same either way, because
					# every rider boards at the camps first.
					self._throw_capacity_exceeded(vehicle, trip.direction, trip.occupancy,
												  limit, self._trip_label(trip))

			# Trips that overlap in time DO share the bus, so no single one of them is
			# at fault and this stays a whole-vehicle question. What it must not do is
			# re-report a peak that was already there: editing one run's timings put this
			# bus in play, and a pre-existing overload then refused the edit here instead
			# of in the per-trip check above - the same wall, one line further down.
			#
			# So the peak is judged against what this save INHERITED. A save is refused
			# only when it pushes the bus past what it was already carrying, which still
			# blocks every overload this save actually creates or worsens.
			concurrent = _peak_concurrent_headcount(vehicle_trips)
			inherited = _peak_concurrent_headcount(
				[trip for trip in vehicle_trips if (vehicle, trip.key) in untouched_trips]
			)
			if concurrent > max(limit, inherited):
				frappe.throw(
					_(
						"Capacity Exceeded: Total overlapping passengers ({0}) exceeds "
						"vehicle limit ({1})."
					).format(concurrent, limit),
					title=_("{0}: Vehicle Capacity Exceeded").format(vehicle),
				)

	def _rename_duplicate_trip_names(self):
		"""No two runs on one vehicle answer to the same trip name.

		A trip name is how a run is identified on the block, in the "Add Stop to which
		trip?" picker and on the driver's manifest, so two runs called S-106 on one lane
		are indistinguishable everywhere the name is all the reader has.

		The canvas already mints a name by scanning for the next free sequence rather
		than counting the runs - counting re-issued a name the moment any run but the
		last was removed. But it reads that list when the placement dialog
		OPENS and the drop commits later, so two dialogs open at once, or one left open
		while another card is placed, still hand out the same number. Rather than chase
		every path on the board, the rule is enforced here, where they all end up.

		A repair, not a refusal: the plans already carry duplicates and refusing the save
		would strand them. The earliest run keeps the name - it is the one the dispatcher
		has been looking at - and each later claimant takes the next free sequence for
		that vehicle.
		"""
		by_vehicle = self._runs_by_vehicle()
		series_of = _canvas_series() if by_vehicle else {}
		for vehicle, runs in by_vehicle.items():
			# First, a run that sits on the wrong lane for its name is renamed into the
			# lane's own series; only then are the lane's duplicates sorted.
			self._rename_into_series(runs, series_of.get(vehicle))
			taken = {name for run in runs.values() for name in {run["name"]} if name}
			shape = _trip_name_shape(taken)
			if not shape:
				# No name on this lane parses, so there is no series to extend. Renaming
				# into a guessed one would be worse than leaving the clash visible.
				continue

			claimed = {}
			for key in sorted(runs, key=lambda k: (runs[k]["start"], str(k))):
				run = runs[key]
				if not run["name"]:
					continue
				if run["name"] not in claimed:
					claimed[run["name"]] = key
					continue
				fresh = _next_free_trip_name(shape, taken)
				if not fresh:
					continue
				taken.add(fresh)
				for row in run["rows"]:
					row.trip_name = fresh

	def _rename_into_series(self, runs, series):
		"""Rename the runs of one lane whose name belongs to another lane's series.

		A trip name is the vehicle's row on the board plus a sequence ("S-9" + "01"). A
		whole run moved to another vehicle keeps its name, so it reads as a different
		lane's trip. A run is judged by ITS OWN name and (vehicle,
		trip_group) key - never by looking a name up - and only when that name parses:
		a hand-typed one is the dispatcher's, and a vehicle with no series is not on the
		board, so both keep the existing behaviour.

		The mapping for the whole lane is settled before a single row is written. The
		names the lane keeps (runs already in the series, hand-typed ones) are reserved
		first, so a renamed run can never take a name another run keeps; the earliest run
		picks first and keeps its two-digit sequence if that is free.
		"""
		parsed = _parse_series(series)
		if not parsed:
			return

		order = sorted(runs, key=lambda k: (runs[k]["start"], str(k)))
		taken, moving = set(), []
		for key in order:
			name = runs[key]["name"]
			match = TRIP_NAME.match(str(name).strip()) if name else None
			if match and (match.group(1) or "", match.group(2)) != parsed:
				moving.append((key, match.group(3)))
			elif name:
				taken.add(name)

		prefix, number = parsed
		mapping = {}
		for key, sequence in moving:
			fresh = f"{prefix}{number}{sequence}"
			if fresh in taken:
				fresh = _next_free_trip_name(parsed, taken)
			if not fresh:
				continue
			taken.add(fresh)
			mapping[key] = fresh

		for key, fresh in mapping.items():
			# Every row of the run: the cards, the camp legs with no shipment, and both
			# directions that share the trip_group.
			for row in runs[key]["rows"]:
				row.trip_name = fresh
			runs[key]["name"] = fresh

	def _runs_by_vehicle(self) -> dict:
		"""``{vehicle: {trip key: run}}`` over every row, camp legs included.

		Camp legs carry the run's trip_name too, so a rename has to take them with it or
		the drive out of the accommodation would answer to the old name. That is why this
		does not go through ``_logical_trips``, which deliberately drops them.
		"""
		by_vehicle = {}
		for idx, row in enumerate(self.rows):
			if not row.vehicle:
				continue
			# Standalone rows are keyed by position so two of them never merge.
			key = row.trip_group or f"\0row-{idx}"
			run = by_vehicle.setdefault(row.vehicle, {}).setdefault(
				key, {"name": None, "start": _DAY_SECONDS, "rows": []}
			)
			run["rows"].append(row)
			run["name"] = run["name"] or row.trip_name
			start, _end = _row_time_window(row)
			run["start"] = min(run["start"], start)
		return by_vehicle

	def _logical_trips(self, assignments=None) -> list:
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
		rows = card_rows(assignments if assignments is not None else self.rows)
		live = live_headcounts(rows)
		for idx, row in enumerate(rows):
			if not row.vehicle:
				continue
			direction = _row_direction(row)
			# Standalone rows are keyed by position so two of them never merge.
			group = row.trip_group or f"\0row-{idx}"
			# One trip group on one vehicle is one bus run, whichever way its stops
			# travel. Keying the direction in as well split a chained run into two
			# overlapping pseudo-trips, so the check added the same bus to itself
			#.
			key = (row.vehicle, group)
			start, end = _row_time_window(row)
			live_from, live_to = _row_date_range(row)

			trip = trips.get(key)
			if not trip:
				trips[key] = frappe._dict(
					key=key,
					vehicle=row.vehicle,
					direction=direction,
					headcount=row_headcount(row, live),
					start=start,
					end=end,
					live_from=live_from,
					live_to=live_to,
					# Kept so a merged trip can be walked stop by stop;
					# the summed headcount above is meaningless for one.
					rows=[row],
				)
				continue

			trip.rows.append(row)
			# Stops that do not all travel the same way make this a mixed run, walked leg
			# by leg instead of summed - the row's own ``direction`` only ever said MIXED
			# when the Merge Trip modal wrote it back.
			if direction != trip.direction:
				trip.direction = MIXED_DIRECTION
			trip.headcount += row_headcount(row, live)
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

	def _vehicles_this_save_did_not_touch(self, trips) -> set:
		"""Vehicles whose cards are exactly where they were before this save.

		Capacity is judged against the shipments rather than the snapshot on the row, so
		a roster that grew after a card was placed shows up as an overload on a bus
		nobody has touched. Judging it on every save turned one such bus into a wall
		across the whole plan: a drop on a different vehicle could not be saved until the
		untouched one was fixed. The check is for what a save DOES, so a bus it does
		nothing to keeps the verdict it was saved with.
		"""
		if not self.before:
			return set()

		def placement(trips):
			"""``{vehicle: {(trip group, card)}}`` - which cards ride in which run.

			Neither the trip's own key nor the stop numbering can stand in for that. A
			standalone row is keyed by its position, which moves when an unrelated row is
			added. And ``stop_index`` is DERIVED, not stated: ``_stamp_leg_details``
			renumbers every row of every vehicle off the itinerary (physical stops, camp
			legs included) while the canvas round-trips a logical 1..N, and the order
			itself is re-derived from each card's own arrival time. Keying on either
			re-lettered every card on every save, so no bus was ever "untouched" - one
			pre-existing overload then refused every edit anywhere on the plan, on a
			vehicle the dispatcher had never gone near.

			ponytail: membership only, so re-sequencing a merged run's stops without
			adding or removing a card reads as untouched and keeps the verdict it was
			saved with. Add the order back here if stop order ever becomes something the
			dispatcher sets by hand rather than something the itinerary derives.
			"""
			by_vehicle = {}
			for trip in trips:
				by_vehicle.setdefault(trip.vehicle, set()).update(
					(row.trip_group, row.transportation_shipment) for row in trip.rows
				)
			return by_vehicle

		was = placement(self._logical_trips(self.before))
		now = placement(trips)
		return {vehicle for vehicle, cards in now.items() if was.get(vehicle) == cards}

	def _trips_this_save_did_not_touch(self, trips) -> set:
		"""``{(vehicle, trip group)}`` for runs whose cards are exactly as they were.

		The vehicle-level answer above is too coarse. Editing one run's TIMINGS put its
		bus in play, and every other run on that bus was then judged too - so a dispatcher
		adjusting S-703 was refused by a different run on the same vehicle carrying 26
		passengers in 22 seats, a load nothing in this save had touched and nothing in
		this save could fix.

		Same membership rule as above, one level finer: a run nobody added a card to or
		took one off keeps the verdict it was saved with.
		"""
		if not self.before:
			return set()

		def placement(trips):
			by_trip = {}
			for trip in trips:
				by_trip.setdefault((trip.vehicle, trip.key), set()).update(
					(row.trip_group, row.transportation_shipment) for row in trip.rows
				)
			return by_trip

		was = placement(self._logical_trips(self.before))
		now = placement(trips)
		return {key for key, cards in now.items() if was.get(key) == cards}

	def _validate_mixed_trip_legs(self, trip, limit):
		"""Hold every leg of a merged trip to the seat count.

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

	def _trip_label(self, trip) -> str:
		"""What the dispatcher calls this run - S-703 - rather than its internal key.

		"the outbound run on VHL-L-0013" names a bus that may hold five runs, and the
		one at fault is not the one being edited. The trip name is what the lane, the
		drawer and the manifest all print, so it is what the message should say.
		"""
		for row in trip.rows:
			if row.trip_name:
				return row.trip_name
		return ""

	def _throw_capacity_exceeded(self, vehicle, direction, total_passengers, limit,
								 trip_label=None):
		"""Raise the overloading block with the exact seat shortfall (MA4-13 AC4)."""
		dir_label = _("return") if direction == "RETURN" else _("outbound")
		run = _("{0} run {1}").format(dir_label, trip_label) if trip_label else _("{0} run").format(dir_label)
		frappe.throw(
			_(
				"Capacity Exceeded: the {0} on {1} carries {2} passengers but the "
				"vehicle takes {3}. You are short {4} seat(s) — assign a larger bus or "
				"arrange a taxi."
			).format(run, vehicle, total_passengers, limit, total_passengers - limit),
			title=_("Vehicle Capacity Exceeded"),
		)



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


def _trip_name_shape(names):
	"""``(prefix, vehicle number)`` shared by the trip names already on one lane.

	Read back off the lane rather than re-derived: the canvas numbers a vehicle by its
	POSITION in the vehicle list, which moves as vehicles are added, retired or
	filtered, and is not something the server can reproduce. Whatever the board has
	been calling this bus is what a new name for it has to look like.

	The commonest shape wins, so one odd name left by hand cannot re-letter the lane.
	"""
	shapes = {}
	for name in names:
		match = TRIP_NAME.match(str(name or "").strip())
		if match:
			prefix, vehicle_number, _seq = match.groups()
			shapes[(prefix or "", vehicle_number)] = shapes.get((prefix or "", vehicle_number), 0) + 1
	if not shapes:
		return None
	return max(shapes, key=lambda shape: (shapes[shape], shape))


def _parse_series(series):
	"""``"S-9"`` -> ``("S-", "9")``, ``"26"`` -> ``("", "26")``; None when it is not one."""
	match = re.match(r"^(S-)?(\d+)$", str(series or "").strip())
	if not match:
		return None
	return (match.group(1) or "", match.group(2))


def _canvas_series() -> dict:
	"""``{vehicle: series}`` exactly as the canvas numbers its lanes.

	Imported on the spot because the page module imports this one. A failure to read
	the board's vehicle list must not stop a plan saving, so it falls back to no series
	- which is the behaviour before the series existed.
	"""
	try:
		from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
			canvas_trip_series,
		)

		return canvas_trip_series() or {}
	except Exception:
		frappe.log_error(title="Route Plan: canvas trip series unavailable")
		return {}


def _next_free_trip_name(shape, taken):
	"""The lowest sequence in this lane's series that nothing is using yet.

	Two digits, as the canvas writes them. A lane that has somehow used all 99 gets
	nothing rather than a name that would collide again.
	"""
	prefix, vehicle_number = shape
	for seq in range(1, 100):
		name = f"{prefix}{vehicle_number}{seq:02d}"
		if name not in taken:
			return name
	return None


def _passenger_limits(vehicle_names) -> dict:
	"""``{vehicle: passengers it may carry}`` for the vehicles on a plan.

	The stored ``custom_max_passenger_capacity`` is what the Vehicle form shows,
	so it is what the dispatcher is held to. It is derived on every Vehicle save
	and backfilled by patch, but a record that has somehow never been through
	either would read 0 and wave everything through — so the same formula is
	applied on the spot instead.
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
	aboard at once and the sum is a total the bus never carries.
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
	live = live_headcounts(by_index)
	stops = [
		{
			"headcount": row_headcount(row, live),
			"boards": (directions.get(row.transportation_shipment) or _row_direction(row))
			== "RETURN",
		}
		for row in by_index
	]
	peak, worst_leg, _legs = leg_occupancy(stops)
	return peak, worst_leg


def live_headcounts(rows) -> dict:
	"""{shipment: headcount} read from the shipments these rows point at (#6818).

	A Route Plan Assignment stores a snapshot taken when the card was dropped and never
	refreshes it, while the board draws its cards from the shipments - so a card that has
	since gained or lost an employee leaves the plan holding a number nobody can see. It
	cuts both ways, and the dangerous way is under-counting: a stale row waved a
	28-passenger load through on a 27-seat bus.
	"""
	names = list({row.transportation_shipment for row in card_rows(rows) if row.transportation_shipment})
	if not names:
		return {}
	return {
		doc.name: cint(doc.headcount)
		for doc in frappe.get_all(
			"Transportation Shipment", filters={"name": ["in", names]},
			fields=["name", "headcount"],
		)
	}


def row_headcount(row, live) -> int:
	"""What this row actually carries: the shipment's count, the row's if the card is gone."""
	if row.transportation_shipment in live:
		return cint(live[row.transportation_shipment])
	return cint(row.headcount)


def card_rows(rows) -> list:
	"""The rows that stand for a card, which is every row that decides anything.

	A plan also lists the stops the bus makes that no card is filed against - the
	accommodation it loads at - so the table reads like the itinerary and the leg out of
	the camp has somewhere to keep its minutes. Those rows are a description of the run,
	not a placement: counting one would double a card's riders, and building an itinerary
	from one would visit its stop twice.
	"""
	return [row for row in rows if not cint(row.get("is_camp_leg"))]


def _cards_for_itinerary(rows) -> list:
	"""The rows as card-shaped records build_itinerary can read, in run order.

	The headcount comes from the shipment rather than the row, for the reason
	live_headcounts explains.
	"""
	rows = card_rows(rows)
	names = [row.transportation_shipment for row in rows if row.transportation_shipment]
	if not names:
		return []

	facts = {
		doc.name: doc
		for doc in frappe.get_all(
			"Transportation Shipment",
			filters={"name": ["in", list(set(names))]},
			fields=["name", "accommodation", "accommodation_name", "stop_location",
					"trip_direction", "pre_merge_trip_direction", "start_time", "end_time",
					"headcount"],
		)
	}

	cards = []
	for row in rows:
		fact = facts.get(row.transportation_shipment)
		if not fact:
			continue
		# Where the operator has this block on the lane, which is the order they have
		# stated for the run. Carried alongside the card rather than on it: the card is
		# the shipment's own facts and nothing downstream should read a plan detail off it.
		cards.append((_iso_time_of_day(row.start_time), frappe._dict({
			"name": fact.name,
			"accommodation": fact.accommodation,
			"accommodation_name": fact.accommodation_name,
			"stop_location": fact.stop_location or row.stop_location,
			"headcount": cint(fact.headcount) if fact.headcount is not None else cint(row.headcount),
			"trip_direction": fact.trip_direction,
			"pre_merge_trip_direction": fact.pre_merge_trip_direction,
			"start_time": fact.start_time,
			"end_time": fact.end_time,
		})))

	# In the order the operator has the run, which is how the trip modal and the drawer
	# order the same cards. This used to re-derive the order from each card's own shift
	# times so that the modal and the save could not disagree; they still cannot, but
	# both now read the stated order instead of rebuilding one, so a stop dragged in the
	# drawer stays where it was put. Sorting on the stored stop_index is
	# still wrong - that is the PHYSICAL stop number, camp stops included, rewritten
	# from the itinerary on every save.
	from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
		run_order,
	)

	cards.sort(key=lambda pair: run_order(pair[1], pair[0]))
	return [card for _placed, card in cards]


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

	Shared by the Route Plan validation and the canvas merge preview, so the
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


# ── Saving the board ────────────────────────────────────────────────────────
#
# A stored record and a canvas item are the same card when route_plan and card_id match.
# card_id is the "TSHIP-<shipment>" id printed on the card, unique per plan (the unique
# key on Route Plan Assignment enforces it). Camp legs match on their own card_id
# "CAMPLEG|<trip group>|<stop>".
#
# A card has changed only when a field the planner sets differs from what is stored.
# start_time and end_time are compared as (date, second of the day): the board rebuilds
# the stamp text, and the date half is the lock lifespan it hands back unchanged.
PLANNER_FIELDS = (
	"vehicle", "trip_group", "trip_name", "transit_minutes", "buffer_minutes", "direction",
	"start_time", "end_time",
)
# Derived from the run by _stamp_leg_details. Written when the card's run is saved, never
# a reason on their own: the board round-trips a logical stop number, not the physical one.
DERIVED_FIELDS = (
	"max_passenger_capacity", "stop_index", "action_type", "current_passenger_count",
	"boarding_count", "drop_off_count", "is_accommodation_origin", "origin_location",
	"shift_start_time", "is_next_day", "qoa_time",
)
# Copies written with the row and never compared: headcount is the live shipment count on
# the board, and the four names are back-filled from the shipment on load.
COPIED_FIELDS = (
	"card_id", "transportation_shipment", "headcount", "site", "shift", "accommodation",
	"stop_location", "is_camp_leg", "is_home_leg",
)
WRITTEN_FIELDS = PLANNER_FIELDS + DERIVED_FIELDS + COPIED_FIELDS
_STAMP_FIELDS = ("start_time", "end_time")
_TIME_FIELDS = ("qoa_time", "shift_start_time")
_TEXT_FIELDS = (
	"vehicle", "trip_group", "trip_name", "direction", "action_type", "origin_location",
	"card_id", "transportation_shipment", "site", "shift", "accommodation", "stop_location",
)


def _comparable(field, value):
	"""``value`` in the form two copies of one field are compared in."""
	if field in _STAMP_FIELDS:
		day = _iso_to_date(value)
		return (day, _iso_time_of_day(value)) if day else (str(value) if value else None)
	if field in _TIME_FIELDS:
		# A Time of 00:00:00 is timedelta(0), which is falsy - test for blank explicitly.
		return None if value is None or value == "" else to_timedelta(value).total_seconds()
	if field in _TEXT_FIELDS:
		return str(value) if value else ""
	return cint(value)


def differs(old, new, fields) -> bool:
	return any(_comparable(f, old.get(f)) != _comparable(f, new.get(f)) for f in fields)


def run_group(row) -> str:
	"""The trip group a row belongs to; a standalone card is a run of its own."""
	if row.trip_group:
		return row.trip_group
	card_id = str(row.card_id or "")
	return card_id.split("|")[1] if cint(row.get("is_camp_leg")) and "|" in card_id else card_id


def run_key(row) -> tuple:
	return (row.vehicle, run_group(row))


def diff_cards(stored_cards, proposed) -> tuple:
	"""``(inserts, updates, deletes)`` as card ids, by the identity rule above."""
	inserts = [card for card in proposed if card not in stored_cards]
	deletes = [card for card in stored_cards if card not in proposed]
	updates = [
		card for card in proposed
		if card in stored_cards and differs(stored_cards[card], proposed[card], PLANNER_FIELDS)
	]
	return inserts, updates, deletes


def _leg_signature(held):
	"""What a run's camp and home legs say, without the lifespan date the board rebases."""
	held = held or {}
	home = held.get("home") or {}
	return (
		_iso_time_of_day(held.get("departure")),
		_iso_time_of_day(held.get("arrival")),
		tuple(sorted(
			(place, cint(m.get("transit_minutes")), cint(m.get("buffer_minutes")))
			for place, m in (held.get("camps") or {}).items()
		)),
		(cint(home.get("transit_minutes")), cint(home.get("buffer_minutes"))),
	)


def apply_plan_changes(plan, items, leg_timings=None, known=None) -> dict:
	"""Write what the posted board changes in ``plan``, and nothing else.

	A card is matched to its record by card_id (see the identity rule above). A card that
	is new, moved, retimed or removed is written, and so is every row of the runs it left
	or joined - their stop numbers, counts and camp legs follow it. Every other record is
	left alone, and a board that changes nothing writes nothing.

	Several planners can save one plan at once. The rows the rules judge are read with a
	lock on every vehicle the save touches (plus the vehicles holding its trip groups), in
	vehicle order, so saves on different vehicles never wait on each other and two saves
	on one vehicle are judged one after the other. ``known`` is ``{card_id: modified}`` as
	the board last saw each record: a record changed since then by someone else is left as
	it is and handed back under "stale" rather than undone. None treats every record as
	seen, which is how a board opened before this existed behaves.

	Runs inside the request transaction: a refused rule rolls back every write, shipment
	statuses included.
	"""
	from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
		_normalize_direction,
		_shift_by_shipment,
		_shipment_direction_flags,
		_shipment_from_card_id,
		_stamp_leg_details,
		_sync_shipment_statuses,
		_unmerge_unmixed_placements,
		_with_stop_indexes,
		card_row_values,
		fold_leg_timings,
		plan_payload,
	)

	frappe.has_permission("Route Plan", "write", plan, throw=True)
	legs = leg_timings or {}
	stored = get_plan_rows(plan)
	stored_cards = {row.card_id: row for row in card_rows(stored)}
	items_by_card = {item.get("cardId", ""): item for item in items}

	# A card that has left a merged run takes its own direction back before its row is
	# built, because a row's direction is read off its shipment.
	def may_have_left_a_merge(card, item):
		row = stored_cards.get(card)
		return not row or (
			_normalize_direction(item.get("direction")) != (row.direction or "")
			or (item.get("vehicleId") or "") != (row.vehicle or "")
			or (item.get("tripId") or "") != (row.trip_group or "")
		)

	moved = {
		_shipment_from_card_id(card) for card, item in items_by_card.items()
		if may_have_left_a_merge(card, item)
	}
	_unmerge_unmixed_placements(
		[item for item in items if _shipment_from_card_id(item.get("cardId", "")) in moved]
	)
	directions = _shipment_direction_flags(items)
	shifts = _shift_by_shipment(items)
	board = {
		item.get("cardId", ""): card_row_values(item, directions, shifts)
		for item in _with_stop_indexes(items)
	}

	# Lock what the save touches, re-read it fresh, and decide again: a locking read sees
	# the latest committed rows where the first read only saw this transaction's
	# snapshot. A fresh row can pull in another vehicle, so repeat until nothing new.
	locked, vanished = set(), set()
	while True:
		change = _plan_changes(stored, board, legs, known, vanished, fold_leg_timings)
		if not change.runs or change.vehicles <= locked:
			break
		fresh_vehicles = sorted(change.vehicles - locked)
		fresh = get_plan_rows(plan, vehicles=fresh_vehicles, for_update=True)
		locked.update(fresh_vehicles)
		stored, gone = _with_fresh_rows(stored, fresh, set(fresh_vehicles))
		vanished |= gone

	stored_cards = {row.card_id: row for row in card_rows(stored)}
	stale = _stale_items(change.stale, stored_cards, plan_payload)
	inserts, updates, deletes = change.inserts, change.updates, change.deletes
	proposed, runs, vehicles = change.proposed, change.runs, change.vehicles

	if not runs:
		header = frappe.db.get_value("Route Plan", plan, "last_modified_at")
		return {
			"status": "ok", "unchanged": 1, "plan_name": plan,
			"saved_at": str(header) if header else None,
			"assignment_count": len(stored), "trip_names": {}, "modified": {}, "stale": stale,
		}

	merged = []
	for row in stored:
		if cint(row.is_camp_leg):
			if row.vehicle in vehicles and run_key(row) not in runs:
				merged.append(frappe._dict(row))
			continue
		new = proposed.get(row.card_id)
		if not new:
			continue
		if run_key(new) in runs:
			merged.append(frappe._dict(new, name=row.name, idx=row.idx))
		elif row.vehicle in vehicles:
			merged.append(frappe._dict(row))
	merged.extend(frappe._dict(proposed[card]) for card in inserts)

	merged.extend(
		frappe._dict(values)
		for values in _stamp_leg_details(
			[row for row in merged if run_key(row) in runs], legs
		)
	)

	PlanRules(merged, [row for row in stored if row.vehicle in vehicles]).run()

	# Stored rows of the scope that this save re-stamped or the trip-name repair renamed;
	# a camp leg with a name here belongs to a run the save did not touch.
	by_name = {row.name: row for row in stored}
	to_update = [
		row for row in merged
		if row.get("name") and differs(by_name[row.name], row, PLANNER_FIELDS + DERIVED_FIELDS)
	]
	to_insert = [row for row in merged if not row.get("name") and not cint(row.is_camp_leg)]
	to_delete = [stored_cards[card].name for card in deletes]

	# A run's camp legs are replaced together, so they stay in the order the run makes
	# its stops - the load reads the departure off the first of them.
	new_legs, old_legs = {}, {}
	for row in merged:
		if cint(row.is_camp_leg) and not row.get("name"):
			new_legs.setdefault(run_key(row), []).append(row)
	for row in stored:
		if cint(row.is_camp_leg) and run_key(row) in runs:
			old_legs.setdefault(run_key(row), []).append(row)
	for key in runs:
		old, new = old_legs.get(key, []), new_legs.get(key, [])
		if [r.card_id for r in old] == [r.card_id for r in new] and not any(
			differs(o, n, WRITTEN_FIELDS) for o, n in zip(old, new)
		):
			continue
		to_delete.extend(row.name for row in old)
		to_insert.extend(new)

	written = _write_plan_rows(plan, stored, to_delete, to_update, to_insert)

	placed = {_shipment_from_card_id(card) for card in board}
	_sync_shipment_statuses(
		[items_by_card[card] for card in written if card in items_by_card],
		{stored_cards[card].transportation_shipment for card in deletes} - placed - {None, ""},
	)

	# Last, so the plan row is locked only for the tail of the save.
	saved_at = frappe.utils.now()
	frappe.db.set_value(
		"Route Plan", plan,
		{"last_modified_by_user": frappe.session.user, "last_modified_at": saved_at},
	)

	return {
		"status": "ok",
		"plan_name": plan,
		"saved_at": saved_at,
		"assignment_count": len(stored) - len(to_delete) + len(to_insert),
		"changed": {
			"inserted": len(inserts), "updated": len(updates), "deleted": len(deletes),
		},
		# The trip names the plan actually STORED on the vehicles this save touched: a
		# duplicate on a vehicle, or a name in another lane's series, is repaired on save,
		# and the board would otherwise keep showing the old name. "vehicle|trip_group",
		# because one trip_group can sit on two vehicles under two names.
		"trip_names": {
			f"{row.vehicle}|{row.trip_group}": row.trip_name
			for row in merged
			if row.vehicle and row.trip_group and row.trip_name
		},
		"modified": written,
		"stale": stale,
	}


def _same_stamp(seen, modified) -> bool:
	return bool(seen) and str(get_datetime(seen)) == str(get_datetime(modified))


def _plan_changes(stored, board, legs, known, vanished, fold_leg_timings):
	"""What the board changes against ``stored``, and the runs and vehicles it touches.

	A stored card the board shows at a version it did not last see is someone else's
	change: it is left as stored and reported stale, and so is a stored card the board
	never saw at all. A card that left the locked vehicles since the first read is
	skipped rather than inserted again.
	"""
	stored_cards = {row.card_id: row for row in card_rows(stored)}
	proposed, stale = {}, []
	for card, values in board.items():
		row = stored_cards.get(card)
		if card in vanished and not row:
			continue
		if row and known is not None and not _same_stamp(known.get(card), row.modified):
			stale.append(card)
			proposed[card] = row
			continue
		proposed[card] = values
	for card, row in stored_cards.items():
		if card not in proposed and known is not None and not _same_stamp(known.get(card), row.modified):
			stale.append(card)
			proposed[card] = row

	inserts, updates, deletes = diff_cards(stored_cards, proposed)
	runs = {run_key(proposed[card]) for card in inserts + updates}
	runs |= {run_key(stored_cards[card]) for card in updates + deletes}
	stored_legs = fold_leg_timings(stored)
	for group in set(legs) | set(stored_legs):
		if _leg_signature(legs.get(group)) != _leg_signature(stored_legs.get(group)):
			runs |= {
				run_key(row) for row in list(proposed.values()) + stored if run_group(row) == group
			}

	# The vehicles this save touches, and every vehicle holding one of its trip groups:
	# the only rule that looks across vehicles is the one-trip-one-vehicle rule.
	groups = {group for _vehicle, group in runs}
	vehicles = {vehicle for vehicle, _group in runs}
	vehicles |= {row.vehicle for row in stored if row.trip_group in groups}
	vehicles.discard(None)
	return frappe._dict(
		proposed=proposed, inserts=inserts, updates=updates, deletes=deletes,
		runs=runs, vehicles=vehicles, stale=stale,
	)


def _with_fresh_rows(stored, fresh, vehicles):
	"""``stored`` with the rows of ``vehicles`` replaced by a fresh read of them.

	Returns the rows and the cards that were on those vehicles and are not any more.
	"""
	fresh_cards = {row.card_id for row in fresh}
	gone = {
		row.card_id for row in stored
		if row.vehicle in vehicles and row.card_id not in fresh_cards
	}
	rows = [
		row for row in stored
		if row.vehicle not in vehicles and row.card_id not in fresh_cards
	] + list(fresh)
	rows.sort(key=lambda row: (cint(row.idx), row.name))
	return rows, gone


def _stale_items(cards, stored_cards, plan_payload) -> list:
	"""The stored version of the cards another planner changed, as the board loads them."""
	rows = [stored_cards[card] for card in cards if card in stored_cards]
	return plan_payload(rows)[0] if rows else []


def check_plan_rows(plan, upserts):
	"""Judge records written outside the board save (the Desk form, Data Import).

	Locks the vehicles the records sit on, were on, and that hold their trip groups, then
	runs PlanRules over the fresh rows with these records in place. The trip-name repair
	applies to the records themselves; the board's leg stamping does not run here.
	"""
	names = [doc.name for doc in upserts if doc.name]
	old = frappe.db.get_values(
		"Route Plan Assignment", {"name": ["in", names or [""]]}, ["vehicle", "trip_group"],
		as_dict=True,
	)
	groups = {row.trip_group for row in list(upserts) + list(old) if row.trip_group}
	vehicles = {row.vehicle for row in list(upserts) + list(old) if row.vehicle}
	if groups:
		vehicles |= {
			row.vehicle for row in get_plan_rows(plan, trip_groups=groups, fields=["vehicle"])
		}
	rows = get_plan_rows(plan, vehicles=sorted(vehicles), for_update=True)
	written = set(names)
	PlanRules([row for row in rows if row.name not in written] + list(upserts), rows).run()


def _write_plan_rows(plan, stored, to_delete, to_update, to_insert) -> dict:
	"""Deletes first, so a card id a delete frees can be inserted again. Returns the
	``{card_id: modified}`` of the card rows written."""
	for name in to_delete:
		frappe.delete_doc(
			"Route Plan Assignment", name, ignore_permissions=True, delete_permanently=True
		)

	written = {}
	for row in to_update:
		doc = frappe.get_doc("Route Plan Assignment", row.name)
		doc.update({field: row.get(field) for field in WRITTEN_FIELDS})
		doc.flags.plan_checked = True
		doc.save(ignore_permissions=True)
		if not cint(doc.is_camp_leg):
			written[doc.card_id] = str(doc.modified)

	idx = max((cint(row.idx) for row in stored), default=0)
	for row in to_insert:
		idx += 1
		doc = frappe.get_doc({
			"doctype": "Route Plan Assignment",
			"route_plan": plan,
			"idx": idx,
			**{field: row.get(field) for field in WRITTEN_FIELDS},
		})
		doc.flags.plan_checked = True
		try:
			doc.insert(ignore_permissions=True)
		except (frappe.UniqueValidationError, frappe.DuplicateEntryError):
			# Two planners dropped the same card on different vehicles at once: their
			# vehicle locks do not overlap, so the unique key decides, and the first wins.
			frappe.throw(
				_("Card {0} was just placed by another planner. The board will reload.").format(
					doc.card_id
				)
			)
		if not cint(doc.is_camp_leg):
			written[doc.card_id] = str(doc.modified)
	return written
