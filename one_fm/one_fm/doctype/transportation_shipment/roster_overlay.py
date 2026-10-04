# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""Who is actually on the bus on a given day.

The shipment generator builds its cards from ``Employee.shift`` - the MASTER allocation.
That answers "whose post is this", not "who is travelling today", and the two part company
constantly: somebody is on leave, somebody else is covering for them.

How leave shows up in this system, confirmed against the live data rather than assumed:

* Approving a Leave Application DELETES the employee's Employee Schedule rows for the
  range (``LeaveApplicationOverride.clear_employee_schedules``) and their Shift
  Assignments (``close_shifts``), then marks Attendance ``On Leave``.
* So there is no "Annual Leave" row on the roster to look for - the row is gone. The
  date-ranged source of truth is the **Leave Application** itself.
* The employee stays ``Active`` with their ``shift`` field intact, which is why they kept
  appearing on transportation cards while away. Six employees were in exactly that state
  on the day this was written.

Relievers are the other half. An ``Employee Schedule`` row with ``is_relieving_schedule``
carries the shift its owner is covering that day and points at the schedule of the person
being covered (2,315 of 2,329 back-links intact). Note that in practice these cover a
**Day Off**, not leave - a reliever has never been linked to a leave-covered schedule,
because the leave flow deletes the schedule they would have pointed at. Both are the same
thing to a bus: a person on today's run who is not on the master allocation.

The overlay is deliberately date-driven and stateless. Nothing is stored, so when a leave
range ends the absent employee simply reappears and their reliever stops being resolved -
which is AC3's "automatic expiration and master plan reversion" with no expiry job to run.
"""

import frappe
from frappe.utils import getdate


def absent_employees(on_date=None, employee_ids=None) -> dict:
	"""``{employee: (from_date, to_date)}`` for approved leave covering ``on_date``.

	Read off Leave Application because that is the only place the RANGE survives: the
	roster rows inside it are deleted on approval, and Attendance records the days one at
	a time without the span the tooltip needs.
	"""
	on_date = getdate(on_date or frappe.utils.today())

	filters = [
		["docstatus", "=", 1],
		["status", "=", "Approved"],
		["from_date", "<=", on_date],
		["to_date", ">=", on_date],
	]
	if employee_ids is not None:
		if not employee_ids:
			return {}
		filters.append(["employee", "in", list(employee_ids)])

	return {
		row.employee: (row.from_date, row.to_date)
		for row in frappe.get_all(
			"Leave Application",
			filters=filters,
			fields=["employee", "from_date", "to_date"],
			# A longer span wins when two overlap, so the tooltip names the absence the
			# operator is most likely asking about.
			order_by="to_date asc",
		)
	}


def relieving_assignments(on_date=None, shift_names=None) -> dict:
	"""``{employee: {...}}`` for people whose schedule has them relieving on ``on_date``.

	``shift`` is the post they are covering that day, which is what decides the bus they
	ride - not the shift on their own Employee record.
	"""
	on_date = getdate(on_date or frappe.utils.today())

	filters = {"date": on_date, "is_relieving_schedule": 1}
	if shift_names is not None:
		if not shift_names:
			return {}
		filters["shift"] = ["in", list(shift_names)]

	rows = frappe.get_all(
		"Employee Schedule",
		filters=filters,
		fields=["employee", "employee_name", "shift", "site",
				"relieving_employee_schedule", "employee_availability"],
	)
	# Only somebody actually working is on the bus; a relieving row marked Day Off is a
	# scheduling artefact, not a passenger.
	rows = [r for r in rows if r.shift and r.employee_availability == "Working"]
	if not rows:
		return {}

	covered = _covered_employees([r.relieving_employee_schedule for r in rows])

	overlay = {}
	for row in rows:
		original = covered.get(row.relieving_employee_schedule) or {}
		overlay[row.employee] = {
			"shift": row.shift,
			"site": row.site,
			"relieving_employee": original.get("employee"),
			"relieving_employee_name": original.get("employee_name"),
			# Why the person being covered is away. Usually "Day Off"; a leave span, when
			# there is one, is filled in by reliever_context below.
			"absence_reason": original.get("employee_availability"),
		}
	return overlay


def _covered_employees(schedule_names) -> dict:
	"""``{schedule: {employee, employee_name, employee_availability}}`` for the covered rows.

	A back-link can dangle - the covered schedule is deleted when the absence turns out to
	be leave - so a missing row is normal and simply leaves the reliever untagged rather
	than dropping them from the bus.
	"""
	names = [name for name in schedule_names if name]
	if not names:
		return {}

	return {
		row.name: row
		for row in frappe.get_all(
			"Employee Schedule",
			filters={"name": ["in", names]},
			fields=["name", "employee", "employee_name", "employee_availability"],
		)
	}


def reliever_context(on_date=None, shift_names=None) -> dict:
	"""The relieving overlay with the covered person's leave span filled in.

	Used to stamp the RELIEVER tag and its tooltip onto the card's roster rows (AC2).
	"""
	overlay = relieving_assignments(on_date, shift_names)
	if not overlay:
		return {}

	covered_ids = {
		data["relieving_employee"] for data in overlay.values() if data.get("relieving_employee")
	}
	spans = absent_employees(on_date, covered_ids) if covered_ids else {}

	for data in overlay.values():
		span = spans.get(data.get("relieving_employee"))
		data["leave_from"], data["leave_to"] = span if span else (None, None)
	return overlay


def apply_to_shift_map(emp_shift_map: dict, on_date=None) -> dict:
	"""Rewrite ``{employee: shift}`` into the people actually travelling on ``on_date``.

	Three moves, in this order:

	1. Anyone on approved leave comes OUT. They are still Active with their shift set, so
	   nothing else would have removed them and they rode a bus they were never on.
	2. Anyone BEING relieved comes out too. Leave is not the only reason somebody is away
	   - in practice it is hardly ever the reason, because the leave flow deletes the
	   schedule a reliever would point at, so relief here is almost always against a Day
	   Off. Without this, the reliever was added while the person they are standing in for
	   stayed on the card, and the seat was counted twice: on the live plan that was 16
	   people riding a bus on their day off, none of whom any other rule would remove.
	3. Anyone relieving that day goes IN, filed under the shift they are COVERING rather
	   than their own - the whole point is that they are on a different run today.

	Note what 2 and 3 together do NOT promise: that the swap is visible on one card. The
	criterion reads as though the reliever's name replaces the absent one in place, and it
	does when the two share a camp - 5 of today's 16. For the other 11 the reliever sleeps
	somewhere else, so the bus that collects the person being covered never passes them.
	The honest result is a rider removed from one camp's card and a new card raised from
	the reliever's own, which is what actually has to happen for either of them to travel.

	Returns a new mapping; the caller's is not modified.
	"""
	resolved = dict(emp_shift_map)

	for employee in absent_employees(on_date, set(resolved)):
		resolved.pop(employee, None)

	for employee, data in relieving_assignments(on_date).items():
		covered = data.get("relieving_employee")
		if covered:
			# The back-link can dangle (_covered_employees explains when), and then there
			# is nobody named to take off - the reliever still boards, which is the safe
			# way round: an extra seat beats a missing passenger.
			resolved.pop(covered, None)
		resolved[employee] = data["shift"]

	return resolved
