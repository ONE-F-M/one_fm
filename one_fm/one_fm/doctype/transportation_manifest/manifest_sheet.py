# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

"""Multi-Accommodation attendance-check sheet API (MA2-11).

Backs the grouped, stop-by-stop attendance/QOA ("Quality of Appearance") check
that supervisors run while a bus boards staff camp-by-camp. The same whitelisted
methods drive both the Frappe desktop render (transportation_manifest.js) and the
Ionic mobile screen, so all business rules live here on the server:

- passengers are grouped into pickup stops (by Stop Sequence + camp), matching the
  physical bus route;
- each stop is Locked, Active, or Completed, driven by a single pointer stored on
  the parent (``active_stop_sequence``);
- stops must be triggered strictly in sequence — Stop N only after Stop N-1 — and
  triggering a stop locks every earlier (completed) stop read-only;
- only the Active stop's Attendance Status / QOA Status may be edited; the server
  rejects writes to any other stop.

A row is flagged a "reliever" when it carries a ``reliever_employee`` (the
replacement assigned when the original worker is Absent or fails QOA), so the
supervisor can tell replacement staff from regular staff at the gate.
"""

import json

import frappe
from frappe import _

# Camp-collapse mirrored from the manifest compiler (kept in sync deliberately) so a
# passenger checked in at any Mahboula sub-camp reads as the one "Mahboula Camp"
# banner on the sheet. Inlined rather than imported to keep this API lightweight.
MAHBOULA_LABELS = {"Mahboula 3", "Mahboula 12", "Mahboula 13", "Mahboula 15"}

STATUS_LOCKED = "Locked"
STATUS_ACTIVE = "Active"
STATUS_COMPLETED = "Completed"


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


def _stop_status(stop_sequence: int, active: int) -> str:
	"""Resolve a stop's lock state from the single active-stop pointer.

	Strictly sequential: stops before the active pointer are Completed (frozen),
	the pointer itself is Active (editable), everything after is Locked.
	"""
	if active and stop_sequence < active:
		return STATUS_COMPLETED
	if active and stop_sequence == active:
		return STATUS_ACTIVE
	return STATUS_LOCKED


def _build_sheet(doc) -> dict:
	"""Assemble the grouped stop/passenger structure the front-ends render.

	Rows are grouped by ``stop_sequence`` (stamped by the controller). Reliever
	names are resolved in one batch. The returned shape is intentionally flat and
	JSON-friendly so the Ionic app and the desktop client can share it verbatim.
	"""
	active = int(doc.active_stop_sequence or 0)

	rows = list(doc.transportation_manifest_details)

	# What happens to each rider AT THE STOP, read from the plan rather than copied onto
	# the manifest: the Route Plan Assignment is where the itinerary is decided, and a
	# second stored copy would be a second answer the moment a trip is re-planned. This
	# is what splits a handover stop into its two sections for the driver (WI-002171).
	leg_facts = _stop_actions(rows)

	# Batch-resolve reliever employee names (rows that actually have a reliever).
	reliever_ids = {r.reliever_employee for r in rows if r.reliever_employee}
	reliever_names = {}
	if reliever_ids:
		for emp in frappe.get_all(
			"Employee",
			filters={"name": ["in", list(reliever_ids)]},
			fields=["name", "employee_name"],
		):
			reliever_names[emp.name] = emp.employee_name

	# Batch-resolve camp display labels.
	acc_ids = {r.pickup_accommodation for r in rows if r.pickup_accommodation}
	labels = _accommodation_labels(list(acc_ids))

	# Group rows by stop sequence, preserving first-seen order for the camp label.
	stops = {}
	order = []
	for row in rows:
		seq = int(row.stop_sequence or 1)
		if seq not in stops:
			stops[seq] = {
				"stop_sequence": seq,
				"accommodation": row.pickup_accommodation,
				"accommodation_label": labels.get(row.pickup_accommodation)
				or row.pickup_accommodation
				or row.stop_name
				or _("Unassigned"),
				"is_adhoc": bool(row.is_adhoc_stop),
				"passengers": [],
			}
			order.append(seq)

		is_reliever = bool(row.reliever_employee)
		stops[seq]["passengers"].append({
			"row_name": row.name,
			"idx": row.idx,
			"employee": row.employee,
			"employee_name": row.employee_name,
			"is_reliever": is_reliever,
			"reliever_employee": row.reliever_employee,
			"reliever_employee_name": reliever_names.get(row.reliever_employee),
			"attendance_status": row.attendance_status,
			"qoa_status": row.qoa_status,
			"qoa_reason": row.qoa_reason,
			"requires_reliever": bool(row.requires_reliever),
			"scheduled_time": str(row.scheduled_time) if row.scheduled_time else None,
			"stop_type": row.stop_type,
			"employee_action": row.employee_action,
			"stop_action": (leg_facts.get(
				(row.trip_id or "", row.transportation_shipment or "")) or {}).get("action_type"),
			# AC 1.5 of WI-002151: an accommodation pickup prints when its driver reports.
			"qoa_time": (leg_facts.get(
				(row.trip_id or "", row.transportation_shipment or "")) or {}).get("qoa_time"),
		})

	stop_list = []
	for seq in sorted(order):
		stop = stops[seq]
		status = _stop_status(seq, active)
		stop["status"] = status
		stop["editable"] = status == STATUS_ACTIVE
		# Sequential gating flags the front-ends echo (real enforcement is server-side).
		stop["can_trigger"] = seq == active + 1
		stop["can_complete"] = seq == active
		stop_list.append(stop)

	max_stop = max(order) if order else 0

	return {
		"manifest": doc.name,
		"schedule_date": str(doc.schedule_date) if doc.schedule_date else None,
		"vehicle_no": doc.vehicle_no,
		"license_plate": doc.license_plate,
		"active_stop_sequence": active,
		"max_stop": max_stop,
		"all_completed": bool(max_stop and active > max_stop),
		"can_edit": doc.has_permission("write"),
		"stops": stop_list,
	}


@frappe.whitelist()
def get_manifest_sheet(manifest: str) -> dict:
	"""Return the grouped, stop-by-stop attendance sheet for a manifest.

	Read-only; enforces document read permission. Shared by the desktop render and
	the Ionic mobile screen.
	"""
	doc = frappe.get_doc("Transportation Manifest", manifest)
	doc.check_permission("read")
	return _build_sheet(doc)


def _set_active_stop(manifest: str, new_active: int) -> dict:
	"""Persist the active-stop pointer and return the refreshed sheet."""
	doc = frappe.get_doc("Transportation Manifest", manifest)
	doc.check_permission("write")
	# db_set persists immediately without re-running the full save cycle, so the
	# lock pointer moves atomically even if a supervisor never presses Save.
	doc.db_set("active_stop_sequence", new_active)
	doc.reload()
	return _build_sheet(doc)


@frappe.whitelist(methods=["POST"])
def trigger_attendance_check(manifest: str, stop_sequence) -> dict:
	"""Unlock a stop for attendance/QOA checks, locking every earlier stop.

	Strictly sequential: a stop can only be triggered once the previous stop is
	complete (``stop_sequence == active + 1``). Triggering advances the pointer,
	which automatically freezes all preceding (completed) stops read-only.
	"""
	stop_sequence = int(stop_sequence)
	doc = frappe.get_doc("Transportation Manifest", manifest)
	doc.check_permission("write")

	active = int(doc.active_stop_sequence or 0)
	if stop_sequence != active + 1:
		if stop_sequence <= active:
			frappe.throw(
				_("Stop {0} has already been triggered — completed stops stay locked.").format(stop_sequence)
			)
		frappe.throw(
			_("Stop {0} cannot be started yet. Complete Stop {1} first.").format(stop_sequence, active + 1)
		)

	return _set_active_stop(manifest, stop_sequence)


@frappe.whitelist(methods=["POST"])
def complete_stop(manifest: str, stop_sequence) -> dict:
	"""Mark the currently active stop complete and lock it read-only.

	Advances the pointer past the active stop (``active + 1``). This is how the
	final stop gets locked, and how a supervisor can freeze the current stop before
	physically arriving at the next one.
	"""
	stop_sequence = int(stop_sequence)
	doc = frappe.get_doc("Transportation Manifest", manifest)
	doc.check_permission("write")

	active = int(doc.active_stop_sequence or 0)
	if stop_sequence != active:
		frappe.throw(
			_("Only the active stop (Stop {0}) can be completed.").format(active or "—")
		)

	return _set_active_stop(manifest, stop_sequence + 1)


@frappe.whitelist(methods=["POST"])
def save_stop_checks(manifest: str, stop_sequence, updates) -> dict:
	"""Save Attendance Status / QOA Status edits for the active stop only.

	Rejects any write to a row that is not part of the currently active stop, so
	completed and not-yet-reached stops cannot be altered through this endpoint.
	Delegates to a normal ``doc.save()`` so the manifest controller's reliever /
	Rambo-assignment logic still runs.

	``updates`` is a JSON list of
	``{row_name, attendance_status, qoa_status, qoa_reason}``.
	"""
	stop_sequence = int(stop_sequence)
	if isinstance(updates, str):
		updates = json.loads(updates)

	doc = frappe.get_doc("Transportation Manifest", manifest)
	doc.check_permission("write")

	active = int(doc.active_stop_sequence or 0)
	if stop_sequence != active:
		frappe.throw(
			_("Stop {0} is locked. Only the active stop (Stop {1}) can be edited.").format(
				stop_sequence, active or "—"
			)
		)

	rows_by_name = {row.name: row for row in doc.transportation_manifest_details}
	editable_fields = ("attendance_status", "qoa_status", "qoa_reason")

	for update in updates:
		row_name = update.get("row_name")
		row = rows_by_name.get(row_name)
		if not row:
			frappe.throw(_("Manifest row {0} not found.").format(row_name))
		if int(row.stop_sequence or 1) != stop_sequence:
			# Defensive: the payload references a row outside the active stop.
			frappe.throw(
				_("Row {0} does not belong to Stop {1} and cannot be edited here.").format(
					row.idx, stop_sequence
				)
			)
		for field in editable_fields:
			if field in update:
				row.set(field, update.get(field))

	doc.save()
	doc.reload()
	return _build_sheet(doc)


def _stop_actions(rows) -> dict:
	"""{(trip_group, shipment): {action_type, qoa_time}} for the legs these rows came from.

	One batched read rather than a lookup per row, and nothing is stored: the plan says
	what happens at each stop, so the manifest asks it instead of keeping its own copy
	that would go stale the moment the trip is re-planned.
	"""
	keys = {
		(row.trip_id or "", row.transportation_shipment or "")
		for row in rows
		if row.trip_id and row.transportation_shipment
	}
	if not keys:
		return {}

	assignments = frappe.get_all(
		"Route Plan Assignment",
		filters={
			"trip_group": ["in", sorted({key[0] for key in keys})],
			"transportation_shipment": ["in", sorted({key[1] for key in keys})],
			# A camp leg links the same shipment and shares its trip group, so without
			# this it would answer for the card's stop and hand the sheet "Boarding" at
			# a site where the riders are being put down.
			"is_camp_leg": 0,
		},
		fields=["trip_group", "transportation_shipment", "action_type", "qoa_time"],
	)
	return {
		(row.trip_group, row.transportation_shipment): {
			"action_type": row.action_type,
			"qoa_time": str(row.qoa_time) if row.qoa_time else None,
		}
		for row in assignments
	}
