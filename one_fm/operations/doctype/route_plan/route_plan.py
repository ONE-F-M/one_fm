# Copyright (c) 2026, oneaborance and contributors
# For license information, please see license.txt

import datetime

import frappe
from frappe import _
from frappe.utils import cint, getdate, to_timedelta
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

	def before_save(self):
		self.last_modified_by_user = frappe.session.user
		self.last_modified_at = frappe.utils.now()


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


def _format_lock_until(end_time) -> str:
	"""Render a Time value as a 12-hour clock label, e.g. ``02:00 PM``."""
	if not end_time:
		return ""
	total = int(to_timedelta(end_time).total_seconds())
	hours = (total // 3600) % 24
	minutes = (total % 3600) // 60
	return datetime.time(hours, minutes).strftime("%I:%M %p")
