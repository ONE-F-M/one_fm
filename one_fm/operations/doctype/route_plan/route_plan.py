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
		"""Block a merged run whose combined headcount exceeds the bus seats (MA4-13).

		Multiple accommodation cards from different camps dropped on one vehicle
		for the same shift share a ``trip_group`` hash. Each physical run is one
		direction of that trip, so we sum the ``headcount`` of every assignment
		row sharing a ``(vehicle, trip_group, direction)`` and compare it against
		the assigned Vehicle's legal seat count, reserving one seat for the driver
		(consistent with the route optimizer's ``seats - 1`` load limit). When the
		combined mixed-passenger total overshoots, the save is rejected with the
		exact seat shortfall so the dispatcher can assign a larger bus or arrange a
		taxi. Scope is trip_group clusters — the multi-accommodation merge this
		story guards; standalone drops keep their existing client-side check.
		"""
		# Cluster the merged legs and tally their combined demand.
		cluster_headcount = {}
		for row in self.assignments:
			if not row.vehicle or not row.trip_group:
				continue
			key = (row.vehicle, row.trip_group, _row_direction(row))
			cluster_headcount[key] = cluster_headcount.get(key, 0) + cint(row.headcount)

		if not cluster_headcount:
			return

		# Batch-fetch seat counts for every vehicle referenced on the plan.
		vehicle_names = list({key[0] for key in cluster_headcount})
		seats_map = {
			v.name: cint(v.seats)
			for v in frappe.get_all(
				"Vehicle",
				filters={"name": ["in", vehicle_names]},
				fields=["name", "seats"],
			)
		}

		for (vehicle, trip_group, direction), total_passengers in cluster_headcount.items():
			seats = seats_map.get(vehicle)
			if not seats:
				# Vehicle master has no seat count configured — nothing to enforce.
				continue
			# Reserve one seat for the driver: the legal passenger capacity.
			passenger_capacity = max(seats - 1, 0)
			if total_passengers > passenger_capacity:
				self._throw_capacity_exceeded(
					vehicle, direction, total_passengers, passenger_capacity, seats
				)

	def _throw_capacity_exceeded(self, vehicle, direction, total_passengers, passenger_capacity, seats):
		"""Raise the overloading block with the exact seat shortfall (MA4-13 AC4)."""
		short_by = total_passengers - passenger_capacity
		dir_label = _("return") if direction == "RETURN" else _("outbound")
		frappe.throw(
			_(
				"Capacity Exceeded: the {0} run on {1} carries {2} passengers but the "
				"vehicle seats only {3} ({4} total minus the driver). You are short {5} "
				"seat(s) — assign a larger bus or arrange a taxi."
			).format(dir_label, vehicle, total_passengers, passenger_capacity, seats, short_by),
			title=_("Vehicle Capacity Exceeded"),
		)

	def before_save(self):
		self.last_modified_by_user = frappe.session.user
		self.last_modified_at = frappe.utils.now()


def _row_direction(row) -> str:
	"""Normalize an assignment row's direction to OUTBOUND/RETURN.

	The Route Plan Assignment ``direction`` Select stores OUTBOUND/RETURN, but a
	blank or stray value is collapsed to OUTBOUND so a leg is never silently
	dropped from a capacity or single-vehicle cluster.
	"""
	return "RETURN" if (row.direction or "").strip().upper().startswith("RET") else "OUTBOUND"


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
