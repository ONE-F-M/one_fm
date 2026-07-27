# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

"""Daily manifest compilation with reliever clustering and adhoc detour stops (MA1-14).

At midnight the daily scheduler compiles the driver pickup instructions for the
day. The base manifests (general shift workers) are already materialized from the
Active Route Plan by the schedule page's ``get_manifest_data_for_plan`` builder;
this module runs on top of that build and folds in the day's Rambo relievers.

For every reliever scheduled to work a shift today, the compiler:

- resolves the reliever's *live* accommodation (their latest Accommodation Checkin),
- finds the vehicle + trip group already serving that reliever's shift, and
- clusters the reliever under the existing camp stop when their camp is already a
  stop on that trip group (merge — AC1/AC2/AC3/AC7/AC8), otherwise inserts a
  temporary detour stop flagged ``is_adhoc_stop=1`` for that day only
  (AC5/AC6/AC9).

Stop numbering itself is left to the Transportation Manifest controller
(``populate_stop_sequence_and_pickup_accommodation``), which numbers rows per
unique ``pickup_accommodation``. The compiler only has to stamp each reliever row
with the reliever's live camp; merge vs. new-stop then falls out of the numbering
automatically. Per-stop boarding headcount is derived from the row count, so it
updates as relievers are added (AC4).

The pass is idempotent: re-running it (a second scheduler tick, or a manual
recompile) never duplicates a reliever row — an existing reliever row on the same
trip is refreshed in place.
"""

import frappe
from frappe import _
from frappe.utils import today

from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
	_normalize_direction,
	get_manifest_data_for_plan,
)

# Mirror the camp-collapse used across the transport scheduling stack so a
# reliever checked in at any Mahboula sub-camp reads as the one "Mahboula Camp"
# label on the driver's stop.
MAHBOULA_LABELS = {"Mahboula 3", "Mahboula 12", "Mahboula 13", "Mahboula 15"}

# Employee Schedule availabilities that mean the reliever is actually turning up
# for the shift (and therefore needs a pickup). Mirrors rambo_shift_assignment.
WORKING_AVAILABILITY = ("Working", "On-the-job Training", "Client Event")


def _get_active_plan_name() -> str | None:
	"""Resolve the route blueprint the day runs on: default plan, else Active."""
	plan = frappe.db.get_value("Route Plan", {"is_default": 1}, "name")
	if not plan:
		plan = frappe.db.get_value("Route Plan", {"status": "Active"}, "name")
	return plan


def _relievers_scheduled_today(schedule_date: str) -> list:
	"""Rambo relievers scheduled to work a shift on ``schedule_date``.

	Reads Employee Schedule rows flagged ``is_rambo_schedule`` for the date whose
	employee is an active Rambo reliever and who is actually working that day.
	Returns one dict per reliever with the shift and site to attach them to.
	"""
	from frappe.query_builder import DocType

	EmployeeSchedule = DocType("Employee Schedule")
	Employee = DocType("Employee")

	rows = (
		frappe.qb.from_(EmployeeSchedule)
		.inner_join(Employee)
		.on(EmployeeSchedule.employee == Employee.name)
		.select(
			EmployeeSchedule.employee,
			EmployeeSchedule.employee_name,
			EmployeeSchedule.shift,
			EmployeeSchedule.site,
		)
		.where(EmployeeSchedule.date == schedule_date)
		.where(EmployeeSchedule.is_rambo_schedule == 1)
		.where(EmployeeSchedule.employee_availability.isin(list(WORKING_AVAILABILITY)))
		.where(EmployeeSchedule.roster_type.isin(["Basic", "Over-Time"]))
		.where(Employee.status == "Active")
		.where(Employee.custom_is_rambo_reliever == 1)
	).run(as_dict=True)

	# One row per reliever+shift is enough; collapse duplicates (e.g. Basic+OT).
	seen = set()
	relievers = []
	for r in rows:
		if not r.shift:
			continue
		key = (r.employee, r.shift)
		if key in seen:
			continue
		seen.add(key)
		relievers.append(r)
	return relievers


def _live_accommodation(emp_ids: list) -> dict:
	"""Map each employee to their most recent Accommodation Checkin (IN) camp.

	Mirrors the latest-checkin-per-employee resolution used by
	get_grouped_employees_by_accommodation, so a reliever's pickup camp is their
	live location, not a stale roster default. Returns {employee: accommodation}.
	"""
	if not emp_ids:
		return {}

	checkin_rows = frappe.db.sql(
		"""
		SELECT c.employee, c.accommodation
		FROM `tabAccommodation Checkin Checkout` c
		INNER JOIN (
			SELECT employee, MAX(creation) AS max_creation
			FROM `tabAccommodation Checkin Checkout`
			WHERE type = 'IN'
			  AND employee IS NOT NULL
			  AND employee != ''
			  AND employee IN %(emp_ids)s
			GROUP BY employee
		) latest ON c.employee = latest.employee AND c.creation = latest.max_creation
		WHERE c.type = 'IN'
		""",
		{"emp_ids": emp_ids},
		as_dict=True,
	)
	return {r.employee: r.accommodation for r in checkin_rows if r.accommodation}


def _accommodation_labels(acc_ids: list) -> dict:
	"""Map Accommodation id -> display label, collapsing Mahboula sub-camps."""
	if not acc_ids:
		return {}
	labels = {}
	for row in frappe.get_all(
		"Accommodation",
		filters={"name": ["in", list(acc_ids)]},
		fields=["name", "accommodation"],
	):
		label = row.accommodation or row.name
		labels[row.name] = "Mahboula Camp" if label in MAHBOULA_LABELS else label
	return labels


def _outbound_assignments_by_shift(plan_doc) -> dict:
	"""Group the plan's outbound assignment rows by the shift they serve.

	Only outbound (pickup) legs matter for boarding instructions. Returns
	{shift: [assignment_row, ...]} so a reliever's shift resolves to the
	vehicle(s)/trip group(s) already carrying that shift's workers.
	"""
	by_shift = {}
	for row in plan_doc.assignments:
		if _normalize_direction(row.direction) != "OUTBOUND":
			continue
		if not row.shift:
			continue
		by_shift.setdefault(row.shift, []).append(row)
	return by_shift


def _pick_target(candidates: list, camp: str, manifest_stops: dict):
	"""Choose the (vehicle, trip_group) a reliever attaches to, and whether to merge.

	``candidates`` are the outbound assignment rows serving the reliever's shift.
	``manifest_stops`` maps (vehicle, trip_group) -> {pickup_accommodation: repr row}.

	Prefers a candidate whose trip group already stops at the reliever's camp
	(merge). Falls back to the first candidate deterministically (a new adhoc
	detour stop on that trip). Returns (row, is_merge) or (None, False).
	"""
	ordered = sorted(
		candidates,
		key=lambda r: (r.vehicle or "", r.trip_group or "", r.stop_index or 0),
	)
	# Merge target: an existing stop for this camp on a serving trip group.
	for row in ordered:
		stops = manifest_stops.get((row.vehicle, row.trip_group or ""))
		if stops and camp in stops:
			return row, True
	# No existing camp stop -> adhoc detour on the primary serving trip.
	return (ordered[0], False) if ordered else (None, False)


def _build_manifest_stops(manifest_doc) -> dict:
	"""Index a manifest's existing stops by (vehicle, trip_group) -> {camp: row}.

	The representative row per camp carries the stop's name / stop_id / scheduled
	time, which a merged reliever row copies so it boards at the same stop.
	"""
	stops = {}
	for row in manifest_doc.transportation_manifest_details:
		if row.employee_action != "Boarding":
			continue
		camp = row.pickup_accommodation
		if not camp:
			continue
		key = (manifest_doc.vehicle_no, row.trip_id or "")
		stops.setdefault(key, {}).setdefault(camp, row)
	return stops


def _reliever_row_exists(manifest_doc, employee: str, trip_group: str) -> bool:
	"""True if this reliever already has a boarding row on this trip (idempotency)."""
	for row in manifest_doc.transportation_manifest_details:
		if (
			row.employee == employee
			and (row.trip_id or "") == (trip_group or "")
			and row.employee_action == "Boarding"
		):
			return True
	return False


def compile_daily_manifests(schedule_date: str | None = None) -> dict:
	"""Compile today's driver pickup instructions, folding in Rambo relievers.

	Daily scheduler entry point. Rebuilds the base manifests from the Active Route
	Plan, then clusters each scheduled reliever under their live camp — merging
	into an existing stop on the shift's trip group, or inserting a temporary
	adhoc detour stop when the camp is not on the standard route (MA1-14).

	Returns a summary dict of what changed.
	"""
	schedule_date = schedule_date or today()
	summary = {"merged": 0, "adhoc": 0, "skipped": 0, "relievers": 0}

	plan_name = _get_active_plan_name()
	if not plan_name:
		frappe.logger().info("compile_daily_manifests: no default/Active Route Plan; nothing to compile.")
		return summary

	# Build/refresh the base manifests for today (general shift workers). This is
	# the same builder the schedule page uses, so the scheduler and the page stay
	# in lockstep. We only need its side effect (manifests created + synced).
	get_manifest_data_for_plan(plan_name)

	relievers = _relievers_scheduled_today(schedule_date)
	summary["relievers"] = len(relievers)
	if not relievers:
		return summary

	plan_doc = frappe.get_doc("Route Plan", plan_name)
	by_shift = _outbound_assignments_by_shift(plan_doc)

	live_camps = _live_accommodation([r.employee for r in relievers])
	labels = _accommodation_labels(list({c for c in live_camps.values() if c}))

	# Load today's manifests once, keyed by vehicle, so multiple relievers on the
	# same vehicle share one in-memory doc (and one save).
	manifest_docs = {}
	touched = set()

	def _manifest_for(vehicle):
		if vehicle in manifest_docs:
			return manifest_docs[vehicle]
		name = frappe.db.get_value(
			"Transportation Manifest",
			{"vehicle_no": vehicle, "schedule_date": schedule_date},
			"name",
		)
		doc = frappe.get_doc("Transportation Manifest", name) if name else None
		manifest_docs[vehicle] = doc
		return doc

	for reliever in relievers:
		camp = live_camps.get(reliever.employee)
		if not camp:
			frappe.logger().info(
				f"compile_daily_manifests: reliever {reliever.employee} has no live accommodation; skipped."
			)
			summary["skipped"] += 1
			continue

		candidates = by_shift.get(reliever.shift)
		if not candidates:
			# The reliever's shift is not on the route blueprint at all — there is
			# no driver run to attach them to. Nothing we can do here; log for ops.
			frappe.logger().info(
				f"compile_daily_manifests: shift {reliever.shift} for reliever "
				f"{reliever.employee} is not served by any vehicle in plan {plan_name}; skipped."
			)
			summary["skipped"] += 1
			continue

		# Resolve target vehicle/trip and merge-vs-adhoc using the current manifest.
		# Build the stop index per candidate vehicle on demand.
		manifest_stops = {}
		for cand in candidates:
			doc = _manifest_for(cand.vehicle)
			if doc:
				manifest_stops.update(_build_manifest_stops(doc))

		target, is_merge = _pick_target(candidates, camp, manifest_stops)
		if not target:
			summary["skipped"] += 1
			continue

		manifest_doc = _manifest_for(target.vehicle)
		if not manifest_doc:
			frappe.logger().info(
				f"compile_daily_manifests: no manifest for vehicle {target.vehicle} on "
				f"{schedule_date}; reliever {reliever.employee} skipped."
			)
			summary["skipped"] += 1
			continue

		trip_group = target.trip_group or ""

		# Idempotency: never add the same reliever to the same trip twice.
		if _reliever_row_exists(manifest_doc, reliever.employee, trip_group):
			summary["skipped"] += 1
			continue

		stop_label = labels.get(camp, camp)
		# Time-of-day the trip departs (assignment start_time is an ISO timestamp).
		scheduled_time = None
		if target.start_time and "T" in target.start_time:
			scheduled_time = target.start_time.split("T")[1][:8]

		if is_merge:
			# Cluster under the existing camp stop: copy its stop identity so the
			# reliever boards in the same group. Stop numbering is recomputed by the
			# controller on save, keyed on pickup_accommodation.
			repr_row = manifest_stops[(target.vehicle, trip_group)][camp]
			manifest_doc.append("transportation_manifest_details", {
				"stop_name": repr_row.stop_name,
				"stop_id": repr_row.stop_id,
				"employee": reliever.employee,
				"employee_name": reliever.employee_name,
				"trip_id": trip_group,
				"trip_name": target.trip_name or "",
				"stop_type": "Pick Up",
				"employee_action": "Boarding",
				"scheduled_time": repr_row.scheduled_time or scheduled_time,
				"pickup_accommodation": camp,
				# Inherit the stop's flag: merging into a real route stop stays 0;
				# a second reliever joining an earlier reliever's detour stays 1 —
				# the whole stop keeps one consistent adhoc identity.
				"is_adhoc_stop": repr_row.is_adhoc_stop or 0,
				"operations_shift": reliever.shift,
				"operations_site": reliever.site,
				"requires_reliever": 0,
			})
			summary["merged"] += 1
		else:
			# Camp is off the standard route -> temporary detour stop for today only.
			manifest_doc.append("transportation_manifest_details", {
				"stop_name": stop_label,
				"stop_id": f"{camp}|OUTBOUND|ADHOC",
				"employee": reliever.employee,
				"employee_name": reliever.employee_name,
				"trip_id": trip_group,
				"trip_name": target.trip_name or "",
				"stop_type": "Pick Up",
				"employee_action": "Boarding",
				"scheduled_time": scheduled_time,
				"pickup_accommodation": camp,
				"is_adhoc_stop": 1,
				"operations_shift": reliever.shift,
				"operations_site": reliever.site,
				"requires_reliever": 0,
			})
			summary["adhoc"] += 1

		touched.add(target.vehicle)

	# Persist every manifest we changed. The controller re-numbers stop_sequence
	# and pickup_accommodation on save, so merged relievers inherit the existing
	# stop number and adhoc relievers get a fresh one.
	for vehicle in touched:
		doc = manifest_docs.get(vehicle)
		if doc:
			doc.save(ignore_permissions=True)

	frappe.db.commit()
	frappe.logger().info(f"compile_daily_manifests[{schedule_date}]: {summary}")
	return summary
