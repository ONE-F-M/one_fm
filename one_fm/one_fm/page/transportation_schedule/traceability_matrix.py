# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""Employee Traceability Matrix (read only).

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

	Compares the one Working non-Over-Time row with the master shift; an extra Over-Time
	row neither grants nor removes eligibility. Relieving rows are always single-day.
	"""
	working = [
		r
		for r in (schedule_rows or [])
		if r.get("employee_availability") == "Working" and r.get("roster_type") != "Over-Time"
	]
	if len(working) != 1:
		return False
	row = working[0]
	if row.get("is_relieving_schedule"):
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


def _roster_row(schedule_rows):
	"""The row that is today's rostered shift: Working, and Basic over Over-Time."""
	working = [r for r in schedule_rows if r.get("employee_availability") == "Working"]
	basic = [r for r in working if r.get("roster_type") == "Basic"]
	chosen = basic or working
	return chosen[0] if chosen else None


@frappe.whitelist()
def get_traceability_matrix(date: str | None = None, plan: str | None = None) -> dict:
	"""One row per active employee (and per non-active one still on a live card).

	Returns ``{"rows": [...], "synced_at": "..."}``; an unexpected failure comes back as
	``{"status": "error", "message": ...}`` so the drawer can say so. A user without one
	of MATRIX_ROLES gets a PermissionError, not an error payload.
	"""
	frappe.only_for(MATRIX_ROLES)

	try:
		on_date = frappe.utils.getdate(date or frappe.utils.today())
		rows = _build_rows(on_date, plan)
	except Exception:
		frappe.log_error(title="Traceability Matrix", message=frappe.get_traceback())
		return {
			"status": "error",
			"message": _("The traceability matrix could not be built. See the Error Log."),
			"rows": [],
		}

	return {"rows": rows, "synced_at": frappe.utils.now_datetime().strftime("%Y-%m-%d %H:%M:%S")}


def _live_cards() -> tuple:
	"""``({card: status}, {employee: [card, ...]}, {card: trip_direction})`` for the cards the board still shows."""
	from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
		_inactive_shifts,
		_serves_only_inactive_shifts,
	)

	shipments = frappe.get_all(
		"Transportation Shipment",
		filters={"status": ["in", ["Unassigned", "Assigned"]]},
		# aggregated_shifts arrives with a migrate; a site that has not run it yet must
		# still get a matrix, so the column is only asked for when it exists.
		fields=["name", "status", "operations_shift", "trip_direction"]
		+ (["aggregated_shifts"] if frappe.db.has_column("Transportation Shipment", "aggregated_shifts") else []),
	)
	inactive = _inactive_shifts(shipments)
	shipments = [s for s in shipments if not _serves_only_inactive_shifts(s, inactive)]
	if not shipments:
		return {}, {}, {}

	status_of = {s.name: s.status for s in shipments}
	riders = frappe.get_all(
		"Transportation Shipment Employee",
		filters={"parent": ["in", list(status_of)], "parenttype": "Transportation Shipment"},
		fields=["parent", "employee_id"],
		order_by="idx asc",
	)
	cards_of = {}
	for rider in riders:
		if rider.employee_id:
			cards_of.setdefault(rider.employee_id, [])
			if rider.parent not in cards_of[rider.employee_id]:
				cards_of[rider.employee_id].append(rider.parent)
	return status_of, cards_of, {s.name: s.trip_direction for s in shipments}


def _placements(plan) -> dict:
	"""``{shipment: {vehicle_label, trip_id, direction}}`` from the plan, camp legs left out."""
	if not frappe.db.exists("DocType", "Route Plan Assignment"):
		return {}

	if not plan:
		defaults = frappe.get_all("Route Plan", filters={"is_default": 1}, fields=["name"], limit_page_length=1)
		plan = defaults[0].name if defaults else None
	if not plan:
		return {}

	assignments = frappe.get_all(
		"Route Plan Assignment",
		filters={"parent": plan, "parenttype": "Route Plan", "is_camp_leg": 0},
		fields=["transportation_shipment", "card_id", "vehicle", "trip_name", "direction"],
		order_by="idx asc",
	)
	vehicle_names = list({a.vehicle for a in assignments if a.vehicle})
	vehicles = {}
	if vehicle_names:
		vehicles = {
			v.name: v
			for v in frappe.get_all(
				"Vehicle",
				filters={"name": ["in", vehicle_names]},
				fields=["name", "license_plate", "one_fm_vehicle_type"],
			)
		}

	placements = {}
	for row in assignments:
		shipment = row.transportation_shipment
		if not shipment and row.card_id and row.card_id.startswith("TSHIP-"):
			shipment = row.card_id[len("TSHIP-"):]
		if not shipment or not row.vehicle or shipment in placements:
			continue
		vehicle = vehicles.get(row.vehicle)
		label = (vehicle.license_plate if vehicle else None) or row.vehicle
		if vehicle and vehicle.one_fm_vehicle_type:
			label = f"{label} ({vehicle.one_fm_vehicle_type})"
		placements[shipment] = {
			"vehicle_label": label,
			"trip_id": row.trip_name,
			"direction": row.direction,
		}
	return placements


def _employees(extra_ids) -> dict:
	fields = ["name", "employee_name", "designation", "status"]
	# Employee.shift and Employee.project are custom columns; a site that has not
	# migrated yet lacks them, and the matrix must still load there (shift then falls
	# back to the HRMS default_shift, project to the roster shift's project).
	for column in ("shift", "project", "custom_operations_role_allocation"):
		if frappe.db.has_column("Employee", column):
			fields.append(column)
	if "shift" not in fields and frappe.db.has_column("Employee", "default_shift"):
		fields.append("default_shift")

	def _tidy(e):
		e["shift"] = e.get("shift") or e.get("default_shift")
		return e

	employees = {
		e.name: _tidy(e)
		for e in frappe.get_all("Employee", filters={"status": "Active"}, fields=fields)
	}
	missing = [i for i in extra_ids if i not in employees]
	if missing:
		for e in frappe.get_all("Employee", filters={"name": ["in", missing]}, fields=fields):
			employees[e.name] = _tidy(e)
	return employees


def _latest_checkins(employee_ids) -> dict:
	"""``{employee: latest IN row}`` - newest first, so the first one seen wins."""
	latest = {}
	for row in frappe.get_all(
		"Accommodation Checkin Checkout",
		filters={"type": "IN", "employee": ["in", employee_ids]},
		fields=["employee", "accommodation", "accommodation_unit", "bed", "checked_out"],
		order_by="creation desc",
	):
		latest.setdefault(row.employee, row)
	return latest


def _missing_reason(reliever, reliever_name, master_shift, roster_shift):
	if reliever:
		return _("Relieving {0}, but no shipment generated").format(reliever_name)
	if roster_shift and master_shift and roster_shift != master_shift:
		return _("Eligible, but no shipment generated: master shift differs from roster")
	return None


def _build_rows(on_date, plan=None) -> list:
	from one_fm.one_fm.doctype.transportation_shipment.roster_overlay import (
		absent_employees,
		relieving_assignments,
	)
	from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import driver_employees

	card_status, cards_of, card_direction = _live_cards()
	employees = _employees(list(cards_of))
	ids = list(employees)
	if not ids:
		return []

	checkins = _latest_checkins(ids)
	acc_names = list({c.accommodation for c in checkins.values() if c.accommodation})
	camp_labels = {}
	if acc_names:
		camp_labels = {
			a.name: a.accommodation or a.name
			for a in frappe.get_all(
				"Accommodation", filters={"name": ["in", acc_names]}, fields=["name", "accommodation"]
			)
		}

	schedules = {}
	for row in frappe.get_all(
		"Employee Schedule",
		filters={"date": on_date},
		fields=["employee", "shift", "employee_availability", "roster_type", "is_relieving_schedule"],
	):
		schedules.setdefault(row.employee, []).append(row)

	chosen = {emp: _roster_row(rows) for emp, rows in schedules.items()}
	shift_names = {r.shift for r in chosen.values() if r and r.shift}
	shift_names.update(e.shift for e in employees.values() if e.shift)
	shift_times = {}
	if shift_names:
		shift_times = {
			s.name: s
			for s in frappe.get_all(
				"Operations Shift",
				filters={"name": ["in", list(shift_names)]},
				fields=["name", "start_time", "end_time", "project"],
			)
		}

	on_leave = absent_employees(on_date, set(ids))
	relievers = relieving_assignments(on_date)
	drivers = driver_employees(ids)
	placements = _placements(plan)

	rows = []
	for emp_id, emp in employees.items():
		emp_rows = schedules.get(emp_id, [])
		roster = chosen.get(emp_id)
		roster_shift = roster.shift if roster else None
		times = shift_times.get(roster_shift) if roster_shift else None

		checkin = checkins.get(emp_id)
		open_in = bool(checkin) and not checkin.checked_out
		reliever = relievers.get(emp_id) or {}
		reliever_name = reliever.get("relieving_employee_name") or reliever.get("relieving_employee")

		# Assigned cards first, so a rider on an outbound and a return card shows the
		# one that has a vehicle.
		own_cards = sorted(cards_of.get(emp_id, []), key=lambda c: card_status.get(c) != "Assigned")
		card = own_cards[0] if own_cards else None
		ctx = {
			"employee_status": emp.status,
			"card": f"TSHIP-{card}" if card else None,
			"card_status": card_status.get(card) if card else None,
			"placement": placements.get(card) if card else None,
			"has_in": bool(checkin),
			"checked_out": bool(checkin and checkin.checked_out),
			"on_leave": emp_id in on_leave,
			"availabilities": [r.employee_availability for r in emp_rows],
			"is_driver": emp_id in drivers,
			"missing_reason": _missing_reason(reliever, reliever_name, emp.shift, roster_shift),
		}
		result = classify(ctx)

		rows.append({
			"id": emp_id,
			"name": emp.employee_name or emp_id,
			"designation": emp.designation,
			"operations_role": emp.get("custom_operations_role_allocation"),
			"project": emp.get("project")
			or (times.project if times else None)
			or (shift_times.get(emp.shift).project if shift_times.get(emp.shift) else None),
			"master_shift": emp.shift,
			"roster_shift": roster_shift,
			"roster_start": _time_text(times.start_time) if times else None,
			"roster_end": _time_text(times.end_time) if times else None,
			"camp": (camp_labels.get(checkin.accommodation) or checkin.accommodation) if open_in else LIVE_OUT,
			"room": " · ".join(filter(None, [checkin.accommodation_unit, checkin.bed])) if open_in else None,
			"is_reliever": bool(reliever),
			"reliever_name": reliever_name,
			"relieving_employee": reliever.get("relieving_employee"),
			"relieving_employee_name": reliever.get("relieving_employee_name"),
			"status": result["status"],
			"badge_text": result["badge_text"],
			"subtext": result["subtext"],
			"can_be_permanent": can_be_permanent(
				[dict(r) for r in emp_rows], emp.shift
			),
			"legs": [
				{
					"card": f"TSHIP-{c}",
					"card_status": card_status.get(c),
					"vehicle": (placements.get(c) or {}).get("vehicle_label"),
					"trip": (placements.get(c) or {}).get("trip_id"),
					"direction": card_direction.get(c) or (placements.get(c) or {}).get("direction"),
				}
				for c in own_cards
			],
		})
	return rows


# ─── Adding a rider by hand ───────────────────────────────────────────────────

SCOPES = ("Today Only", "Permanent")
LIVE_STATUSES = ("Unassigned", "Assigned")
PERMANENT_WARNING = (
	"Employee is working a temporary or reliever shift today. Assignment is limited to "
	"single-day to prevent automated midnight reset conflicts."
)


def _assignment_context(employee: str, scope: str, date: str | None):
	"""Checks shared by both endpoints. Returns ``(employee doc fields, date, schedule rows)``."""
	from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import driver_employees

	if scope not in SCOPES:
		frappe.throw(_("Assignment scope must be Today Only or Permanent."))
	on_date = frappe.utils.getdate(date or frappe.utils.today())
	if on_date != frappe.utils.getdate(frappe.utils.today()):
		frappe.throw(_("Employees can only be added for today."))

	fields = ["name", "employee_name", "status", "cell_number"]
	for column in ("shift", "default_shift"):
		if frappe.db.has_column("Employee", column):
			fields.append(column)
	emp = frappe.db.get_value("Employee", employee, fields, as_dict=True)
	if not emp:
		frappe.throw(_("Employee {0} not found.").format(employee))
	if emp.status != "Active":
		frappe.throw(_("Employee {0} is not Active.").format(employee))
	if employee in driver_employees([employee]):
		frappe.throw(_("Employee {0} is a driver and cannot ride as a passenger.").format(employee))
	emp.shift = emp.get("shift") or emp.get("default_shift")

	rows = frappe.get_all(
		"Employee Schedule",
		filters={"employee": employee, "date": on_date},
		fields=["shift", "employee_availability", "roster_type", "is_relieving_schedule"],
	)
	if scope == "Permanent" and not can_be_permanent([dict(r) for r in rows], emp.shift):
		frappe.throw(_(PERMANENT_WARNING))
	return emp, on_date, rows


def _refuse_duplicate(employee: str, direction: str) -> None:
	"""Throw when the employee already rides a live card in this direction (Outward/Return or OUTBOUND/RETURN)."""
	from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import own_direction

	wanted = own_direction(frappe._dict(trip_direction=direction))
	parents = frappe.get_all(
		"Transportation Shipment Employee",
		filters={"parenttype": "Transportation Shipment", "employee_id": employee},
		pluck="parent",
	)
	if not parents:
		return
	for card in frappe.get_all(
		"Transportation Shipment",
		filters={"name": ["in", list(set(parents))], "status": ["in", LIVE_STATUSES]},
		fields=["name", "trip_direction", "pre_merge_trip_direction"],
	):
		if own_direction(card) == wanted:
			frappe.throw(
				_("Employee {0} is already on card TSHIP-{1} in this direction.").format(employee, card.name)
			)


def _rider(emp, accommodation, stop_location, scope, on_date) -> dict:
	return {
		"employee_id": emp.name,
		"employee_name": emp.employee_name,
		"cell_number": emp.cell_number,
		"accommodation": accommodation,
		"stop_location": stop_location,
		"assignment_scope": scope,
		"assigned_on": on_date,
	}


def _vehicle_load(shipment: str) -> dict:
	"""The busiest vehicle the card is placed on: ``{vehicle, limit, load}``, load as it is now."""
	from one_fm.operations.doctype.route_plan.route_plan import (
		_passenger_limits,
		_peak_concurrent_headcount,
		_trip_occupancy,
	)

	worst = {}
	plans = {}
	for row in frappe.get_all(
		"Route Plan Assignment",
		filters={"transportation_shipment": shipment, "parenttype": "Route Plan", "is_camp_leg": 0},
		fields=["parent", "vehicle"],
	):
		if not row.vehicle:
			continue
		plan = plans.setdefault(row.parent, frappe.get_doc("Route Plan", row.parent))
		trips = plan._logical_trips([r for r in plan.assignments if r.vehicle == row.vehicle])
		load = max([_peak_concurrent_headcount(trips)] + [_trip_occupancy(t) for t in trips])
		if load >= worst.get("load", -1):
			worst = {
				"vehicle": row.vehicle,
				"limit": _passenger_limits({row.vehicle}).get(row.vehicle),
				"load": load,
			}
	return worst


@frappe.whitelist(methods=["POST"])
def add_employee_to_shipment(
	shipment: str, employee: str, scope: str, date: str | None = None, override: int = 0
) -> dict:
	"""Put an employee on a live card by hand.

	A pool card takes the rider whatever its size. A placed card asks the Route Plan trip
	model first and returns ``{"over_capacity": True, ...}`` without writing when the
	bus has no seat, unless ``override`` is set.
	"""
	from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import _SeatCheck
	from one_fm.one_fm.doctype.transportation_shipment.transportation_shipment import (
		own_direction,
		resolve_shipment_names,
	)

	frappe.only_for(MATRIX_ROLES)
	name = (resolve_shipment_names([shipment]) or [None])[0]
	if not name or not frappe.db.exists("Transportation Shipment", name):
		frappe.throw(_("Shipment {0} not found.").format(shipment))
	doc = frappe.get_doc("Transportation Shipment", name)
	doc.check_permission("write")
	if doc.status not in LIVE_STATUSES:
		frappe.throw(_("Shipment {0} is {1}; only Unassigned or Assigned cards take riders.").format(name, doc.status))

	emp, on_date, _rows = _assignment_context(employee, scope, date)
	_refuse_duplicate(employee, own_direction(doc))

	if doc.status == "Assigned" and not frappe.utils.cint(override):
		# room() writes a trial headcount and restores it, so it runs before the append.
		if _SeatCheck().room(doc.name, frappe.utils.cint(doc.headcount), 1) < 1:
			return {"over_capacity": True, "card_id": f"TSHIP-{doc.name}", **_vehicle_load(doc.name)}

	doc.append(
		"transportation_shipment_employee",
		_rider(emp, doc.accommodation, doc.stop_location, scope, on_date),
	)
	doc.save()
	return {"headcount": doc.headcount, "card_id": f"TSHIP-{doc.name}", "status": doc.status}


@frappe.whitelist(methods=["POST"])
def create_shipment_for_employee(
	employee: str, stop_location: str, direction: str, scope: str, date: str | None = None
) -> dict:
	"""A new pool card for one rostered employee: their camp, today's shift times, one rider.

	Left without a source so the shift generator never claims it. A Today Only card
	carries from/to dates, so deactivate_expired_shipments retires it the next day.
	"""
	frappe.only_for(MATRIX_ROLES)
	frappe.has_permission("Transportation Shipment", "create", throw=True)
	if direction not in ("Outward", "Return"):
		frappe.throw(_("Direction must be Outward or Return."))

	emp, on_date, rows = _assignment_context(employee, scope, date)
	_refuse_duplicate(employee, direction)

	if frappe.db.get_value("Location", stop_location, "location_type") != "Stop Location":
		frappe.throw(_("{0} is not a Stop Location.").format(stop_location))

	checkin = _latest_checkins([employee]).get(employee)
	if not checkin or checkin.checked_out or not checkin.accommodation:
		frappe.throw(_("Employee {0} has no open accommodation check-in.").format(employee))

	roster = _roster_row([dict(r) for r in rows])
	if not roster or not roster.get("shift"):
		frappe.throw(_("Employee {0} is not rostered to work today.").format(employee))
	shift = frappe.db.get_value(
		"Operations Shift", roster["shift"], ["start_time", "end_time", "site", "project"], as_dict=True
	) or frappe._dict()

	doc = frappe.new_doc("Transportation Shipment")
	doc.update({
		"status": "Unassigned",
		"accommodation": checkin.accommodation,
		"stop_location": stop_location,
		"operations_shift": roster["shift"],
		"operations_site": shift.site,
		"project": shift.project,
		"start_time": shift.start_time,
		"end_time": shift.end_time,
		"routing_type_badge": "Direct",
		"trip_direction": direction,
		"is_adhoc_journey": 1,
	})
	if scope == "Today Only":
		doc.from_date = doc.to_date = on_date
	doc.append("transportation_shipment_employee", _rider(emp, checkin.accommodation, stop_location, scope, on_date))
	doc.insert()
	return {"headcount": doc.headcount, "card_id": f"TSHIP-{doc.name}", "status": doc.status}
