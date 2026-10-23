# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""Employee Traceability Matrix (WI-003536, P1 - read only).

One row per active employee, plus anyone non-active who is still sitting on a live
shipment card (that is the whole point of the STALE state), saying where that person is
for the day: which vehicle, which pool card, nothing at all, or no seat needed.

Everything is read in bulk - one query per doctype, never one per employee.
"""

import frappe
from frappe import _

from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import time_is_blank

MATRIX_ROLES = ("Transportation Supervisor", "Transportation Manager", "System Manager")

STATUS_ASSIGNED = "Assigned"
STATUS_POOL = "Pool"
STATUS_MISSING = "Missing"
STATUS_EXEMPT = "Exempt"
STATUS_STALE = "Stale"

LIVE_OUT = "Live-Out"
NON_WORKING = ("Day Off", "Client Day Off")


def classify(employee_ctx) -> dict:
	"""Decide an employee's dispatch state. Pure: no database, no clock.

	``employee_ctx`` keys (all optional, missing means "no"/empty):

	* ``employee_status`` - Employee.status
	* ``card`` - id of the live shipment card the employee is on, or None
	* ``card_status`` - that card's status (``Unassigned`` means it is in the pool)
	* ``placement`` - ``{"vehicle_label", "trip_id"}`` when the card sits on a vehicle
	* ``has_in`` - an Accommodation Checkin Checkout IN row exists
	* ``checked_out`` - the latest IN row has been checked out (no camp)
	* ``on_leave`` - approved leave covers the date
	* ``availabilities`` - Employee Schedule ``employee_availability`` values for the date
	* ``is_driver`` - drives the bus, never a passenger
	* ``missing_reason`` - why they are eligible but unplaced, when known

	Order matters: Stale, Assigned, Pool, Exempt, Missing.
	"""
	ctx = employee_ctx or {}
	card = ctx.get("card")
	has_open_in = bool(ctx.get("has_in")) and not ctx.get("checked_out")

	if card:
		if ctx.get("employee_status") != "Active":
			return _result(STATUS_STALE, _("STALE BLOCK DETECTED"), _("Inactive employee still on card {0}").format(card))
		if not ctx.get("has_in"):
			return _result(STATUS_STALE, _("STALE BLOCK DETECTED"), _("No accommodation check-in, still on card {0}").format(card))
		if ctx.get("checked_out"):
			return _result(STATUS_STALE, _("STALE BLOCK DETECTED"), _("Checked out of accommodation, still on card {0}").format(card))

		if ctx.get("card_status") == "Assigned":
			placement = ctx.get("placement") or {}
			label = placement.get("vehicle_label")
			trip = placement.get("trip_id")
			if label and trip:
				badge = _("{0} · Trip {1}").format(label, trip)
			elif label:
				badge = label
			else:
				badge = _("Assigned · {0}").format(card)
			return _result(STATUS_ASSIGNED, badge, card)
		return _result(STATUS_POOL, _("Unassigned Pool · {0}").format(card), card)

	if not has_open_in:
		return _result(STATUS_EXEMPT, _("Self-Commuting / Exempt"), _(LIVE_OUT))

	availabilities = [a for a in (ctx.get("availabilities") or []) if a]
	has_working_row = "Working" in availabilities
	if ctx.get("on_leave") or not has_working_row:
		if ctx.get("on_leave"):
			subtext = _("Approved leave")
		elif any(a in NON_WORKING for a in availabilities):
			subtext = _(availabilities[0]) if availabilities[0] in NON_WORKING else _("Day Off")
		else:
			subtext = _("Not rostered today")
		return _result(STATUS_EXEMPT, _("No seat needed (on leave)"), subtext)

	if ctx.get("is_driver"):
		return _result(STATUS_EXEMPT, _("Self-Commuting / Exempt"), _("Driver"))

	return _result(
		STATUS_MISSING,
		_("MISSING FROM CARD"),
		ctx.get("missing_reason") or _("Eligible, but no shipment generated"),
	)


def _result(status, badge_text, subtext) -> dict:
	return {"status": status, "badge_text": badge_text, "subtext": subtext}


def can_be_permanent(schedule_rows, master_shift) -> bool:
	"""Whether a permanent (indefinite) allocation is allowed for this employee today.

	True only when exactly one Working row exists, it is not a relieving row, it is not
	Over-Time, and its shift is the employee's own master shift. Anything else is a
	temporary arrangement that must stay single-day.
	"""
	working = [r for r in (schedule_rows or []) if r.get("employee_availability") == "Working"]
	if len(working) != 1:
		return False
	row = working[0]
	if row.get("is_relieving_schedule") or row.get("roster_type") == "Over-Time":
		return False
	return bool(master_shift) and row.get("shift") == master_shift


def _time_text(value):
	"""A stored Time as the local ``HH:MM:SS`` string. Midnight is a real value."""
	if time_is_blank(value):
		return None
	text = str(value)
	# timedelta(hours=9) stringifies as "9:00:00"
	head, _sep, rest = text.partition(":")
	return f"{head.zfill(2)}:{rest}" if rest else text
