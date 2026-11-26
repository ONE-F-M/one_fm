# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

"""Read-only endpoints for the manifest page's camp filter and departure slots, and the lobby board."""

import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.utils import add_days, getdate, now_datetime, today


@frappe.whitelist()
def get_active_accommodations() -> list:
	"""Active accommodations for the camp selector.

	Manifest readers have no Accommodation read permission, so the list is read with
	get_all behind the manifest permission check. Names and stop locations only.
	"""
	frappe.has_permission("Transportation Manifest", "read", throw=True)
	return frappe.get_all(
		"Accommodation",
		filters={"status": "Active"},
		fields=["name", "accommodation", "transport_stop_location"],
		order_by="accommodation asc",
	)


@frappe.whitelist()
def get_trip_time_slots(accommodation: str | None = None, schedule_date: str | None = None) -> list:
	"""Manifest rows of one day grouped by departure (trip_time), earliest first.

	Reads Transportation Manifest Details across every manifest of the date. Rows are
	narrowed to ``accommodation`` (pickup_accommodation) when given. Each slot is
	``{trip_time, trips: [{trip_id, trip_name, vehicle_no, manifest, boarding}],
	vehicles, boarding}``; a vehicle with two trips in one slot counts once.
	"""
	frappe.has_permission("Transportation Manifest", "read", throw=True)
	Manifest = DocType("Transportation Manifest")
	Detail = DocType("Transportation Manifest Details")
	query = (
		frappe.qb.from_(Detail)
		.join(Manifest).on(Detail.parent == Manifest.name)
		.select(
			Detail.trip_time, Detail.trip_id, Detail.trip_name, Detail.employee_action,
			Manifest.vehicle_no, Manifest.name.as_("manifest"),
		)
		.where(Detail.parenttype == "Transportation Manifest")
		.where(Manifest.schedule_date == getdate(schedule_date or today()))
		.where(Manifest.docstatus < 2)
		.where(Detail.trip_time.isnotnull())
		.where(Detail.trip_time != "")
	)
	if accommodation:
		query = query.where(Detail.pickup_accommodation == accommodation)
	return group_slots(query.run(as_dict=True))


def group_slots(rows) -> list:
	"""Slots from detail rows; see get_trip_time_slots."""
	slots = {}
	for row in rows:
		slot = slots.setdefault(row.trip_time, {"trip_time": row.trip_time, "trips": {}})
		key = (row.vehicle_no, row.trip_id or "")
		trip = slot["trips"].setdefault(key, {
			"trip_id": row.trip_id or "",
			"trip_name": row.trip_name or "",
			"vehicle_no": row.vehicle_no,
			"manifest": row.manifest,
			"boarding": 0,
		})
		if row.employee_action == "Boarding":
			trip["boarding"] += 1

	result = []
	for trip_time in sorted(slots):
		trips = sorted(slots[trip_time]["trips"].values(), key=lambda t: (t["vehicle_no"] or "", t["trip_name"]))
		result.append({
			"trip_time": trip_time,
			"trips": trips,
			"vehicles": len({t["vehicle_no"] for t in trips}),
			"boarding": sum(t["boarding"] for t in trips),
		})
	return result


@frappe.whitelist()
def get_lobby_board(accommodation: str) -> dict:
	"""Trips leaving one accommodation, yesterday to tomorrow, for the lobby TV board.

	A trip is a (manifest, trip_id) with a row picked up at this accommodation, or an
	empty run: a camp leg of the active plan starts at this camp's stop and no camp at
	that stop boards on it. Absent and QoA-failed riders are left out, their reliever
	shown in their place; no attendance or QoA value leaves the server.
	"""
	frappe.has_permission("Transportation Manifest", "read", throw=True)
	camp = frappe.db.get_value(
		"Accommodation", accommodation, ["name", "accommodation", "transport_stop_location"], as_dict=True
	)
	if not camp:
		frappe.throw(_("Accommodation {0} not found").format(accommodation), frappe.DoesNotExistError)

	base = getdate(today())
	dates = [add_days(base, -1), base, add_days(base, 1)]
	stop = camp.transport_stop_location
	legs = _camp_legs(stop)
	siblings = set(frappe.get_all("Accommodation", filters={"transport_stop_location": stop}, pluck="name")) if stop else set()
	siblings.add(camp.name)

	Manifest = DocType("Transportation Manifest")
	Detail = DocType("Transportation Manifest Details")

	def detail_query():
		return (
			frappe.qb.from_(Detail)
			.join(Manifest).on(Detail.parent == Manifest.name)
			.where(Detail.parenttype == "Transportation Manifest")
			.where(Manifest.schedule_date.isin(dates))
			.where(Manifest.docstatus < 2)
		)

	own_ids = (
		detail_query().select(Detail.trip_id).distinct()
		.where(Detail.pickup_accommodation == camp.name)
	).run(pluck=True)
	trip_ids = list({t or "" for t in own_ids} | set(legs))
	if not trip_ids:
		return _board(camp, [])

	rows = (
		detail_query()
		.select(
			Detail.parent, Manifest.vehicle_no, Manifest.driver_name, Manifest.schedule_date,
			Detail.trip_id, Detail.trip_name, Detail.trip_time, Detail.employee, Detail.employee_name,
			Detail.employee_action, Detail.stop_name, Detail.scheduled_time, Detail.pickup_accommodation,
			Detail.attendance_status, Detail.qoa_status, Detail.reliever_employee,
			Detail.transportation_shipment,
		)
		.where(Detail.trip_id.isin(trip_ids))
		.orderby(Detail.idx)
	).run(as_dict=True)

	groups = {}
	for row in rows:
		row.trip_id = row.trip_id or ""
		groups.setdefault((row.parent, row.trip_id), []).append(row)

	kept = {}
	for key, trip_rows in groups.items():
		if any(r.pickup_accommodation == camp.name for r in trip_rows):
			kept[key] = trip_rows
		elif key[1] in legs and not any(
			r.employee_action == "Boarding" and r.pickup_accommodation in siblings for r in trip_rows
		):
			kept[key] = trip_rows
	return _board(camp, kept, legs)


def _camp_legs(stop) -> dict:
	"""Camp legs of the active plan that leave ``stop``: trip_group -> {departure, qoa}."""
	from one_fm.one_fm.doctype.transportation_manifest.manifest_compiler import _get_active_plan_name
	from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
		_local_seconds,
		_time_field,
	)

	plan = _get_active_plan_name()
	if not (plan and stop):
		return {}
	legs = {}
	for leg in frappe.get_all(
		"Route Plan Assignment",
		filters={"route_plan": plan, "is_camp_leg": 1, "is_home_leg": 0},
		fields=["trip_group", "origin_location", "stop_location", "start_time", "qoa_time"],
	):
		if not leg.trip_group or (leg.origin_location or leg.stop_location) != stop:
			continue
		clock = _time_field(_local_seconds(leg.start_time))
		held = legs.setdefault(leg.trip_group, {"departure": None, "qoa": None})
		if clock and (not held["departure"] or clock[:5] < held["departure"]):
			held["departure"] = clock[:5]
		if leg.qoa_time and not held["qoa"]:
			held["qoa"] = _hhmm(leg.qoa_time)
	return legs


def _hhmm(value) -> str | None:
	"""A Time value (timedelta or "H:MM:SS") as "HH:MM"."""
	if value in (None, ""):
		return None
	seconds = int(value.total_seconds()) if hasattr(value, "total_seconds") else None
	if seconds is None:
		parts = str(value).split(":")
		seconds = int(parts[0]) * 3600 + int(parts[1]) * 60
	seconds %= 86400
	return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}"


def _riding(rows) -> list:
	"""Riders of ``rows`` as shown in public: absent or QoA-failed riders give way to their reliever."""
	riders, seen = [], set()
	for r in rows:
		if (r.employee, r.employee_action) in seen:
			continue
		seen.add((r.employee, r.employee_action))
		if r.reliever_employee:
			riders.append({"row": r, "reliever": r.reliever_employee})
		elif r.attendance_status != "Absent" and r.qoa_status != "Fail":
			riders.append({"row": r, "reliever": None})
	return riders


def _board(camp, trips_rows, legs=None) -> dict:
	legs = legs or {}
	result = {
		"server_now": str(now_datetime().replace(microsecond=0)),
		"accommodation": camp.name,
		"accommodation_name": camp.accommodation or camp.name,
		"trips": [],
	}
	if not trips_rows:
		return result

	all_rows = [r for rows in trips_rows.values() for r in rows]
	shipments = {
		s.name: s for s in frappe.get_all(
			"Transportation Shipment",
			filters={"name": ["in", list({r.transportation_shipment for r in all_rows if r.transportation_shipment}) or [""]]},
			fields=["name", "trip_direction", "pre_merge_trip_direction", "pair_group"],
		)
	}
	vehicles = {
		v.name: v for v in frappe.get_all(
			"Vehicle",
			filters={"name": ["in", list({r.vehicle_no for r in all_rows if r.vehicle_no}) or [""]]},
			fields=["name", "license_plate", "one_fm_vehicle_type", "custom_max_passenger_capacity", "employee"],
		)
	}
	driver_of = {
		key: rows[0].driver_name or (vehicles.get(rows[0].vehicle_no) or {}).get("employee")
		for key, rows in trips_rows.items()
	}
	people = set(driver_of.values()) | {r.reliever_employee for r in all_rows if r.reliever_employee}
	people.discard(None)
	employees = {
		e.name: e for e in frappe.get_all(
			"Employee", filters={"name": ["in", list(people) or [""]]},
			fields=["name", "employee_name", "cell_number"],
		)
	}
	camp_names = dict(frappe.get_all(
		"Accommodation",
		filters={"name": ["in", list({r.pickup_accommodation for r in all_rows if r.pickup_accommodation}) or [""]]},
		fields=["name", "accommodation"], as_list=True,
	))
	paired = _paired_returns(trips_rows, shipments, camp.name)

	for key, rows in trips_rows.items():
		trip = _trip(key, rows, camp, legs.get(key[1]) or {}, shipments, vehicles, employees, camp_names)
		if not trip:
			continue
		trip["driver"] = (employees.get(driver_of[key]) or {}).get("employee_name") or driver_of[key]
		trip["driver_mobile"] = (employees.get(driver_of[key]) or {}).get("cell_number")
		trip["paired_return"] = paired.get(key)
		result["trips"].append(trip)
	result["trips"].sort(key=lambda t: (t["departure"], t["trip_name"]))
	return result


def _trip(key, rows, camp, leg, shipments, vehicles, employees, camp_names) -> dict | None:
	own = [r for r in rows if r.pickup_accommodation == camp.name]
	riding = [r for r in own if r.employee_action == "Boarding"] or own
	trip_time = next((r.trip_time for r in own if r.trip_time), None) or leg.get("departure")
	trip_time = trip_time or next((r.trip_time for r in rows if r.trip_time), None)
	if not trip_time:
		return None
	schedule_date = getdate(rows[0].schedule_date)

	passengers = []
	for rider in _riding(riding):
		r = rider["row"]
		drop_off = r.stop_name if r.employee_action == "Boarding" else (camp.accommodation or camp.name)
		if rider["reliever"]:
			passengers.append({
				"name": (employees.get(rider["reliever"]) or {}).get("employee_name") or rider["reliever"],
				"drop_off": drop_off, "is_reliever": 1, "replaces": r.employee_name or r.employee,
			})
		else:
			passengers.append({"name": r.employee_name or r.employee, "drop_off": drop_off})

	joins = {}
	for rider in _riding([r for r in rows if r.employee_action == "Boarding" and r.pickup_accommodation != camp.name]):
		place = rider["row"].pickup_accommodation
		label = camp_names.get(place) or place or _("another stop")
		joins[label] = joins.get(label, 0) + 1

	trip_ships = [shipments[r.transportation_shipment] for r in rows if r.transportation_shipment in shipments]
	headings = {s.trip_direction for s in trip_ships if s.trip_direction}
	direction = "Mixed" if "Mixed" in headings or len(headings) > 1 else next(iter(headings), None)
	own_leg = next((
		(s.pre_merge_trip_direction if s.trip_direction == "Mixed" else s.trip_direction)
		for s in (shipments.get(r.transportation_shipment) for r in own) if s
	), None)
	if not own_leg:
		own_leg = "Return" if riding and riding[0].employee_action == "Dropping Off" else "Outward"

	boarding_rows = sorted(
		(r for r in rows if r.employee_action == "Boarding"), key=lambda r: str(r.scheduled_time or "")
	) or sorted(rows, key=lambda r: str(r.scheduled_time or ""))
	vehicle = vehicles.get(rows[0].vehicle_no) or {}
	qoa = leg.get("qoa")
	return {
		"key": f"{key[0]}|{key[1]}",
		"manifest": key[0],
		"trip_id": key[1],
		"trip_name": rows[0].trip_name or key[1],
		"schedule_date": str(schedule_date),
		"trip_time": trip_time,
		"departure": f"{schedule_date}T{trip_time}:00",
		# A QoA later in the day than the departure belongs to the evening before.
		"qoa": qoa,
		"qoa_at": f"{add_days(schedule_date, -1) if qoa and qoa > trip_time else schedule_date}T{qoa}:00" if qoa else None,
		"first_destination": boarding_rows[0].stop_name if boarding_rows else None,
		"direction": direction or own_leg,
		"own_leg": own_leg,
		"vehicle_no": rows[0].vehicle_no,
		"vehicle_type": vehicle.get("one_fm_vehicle_type"),
		"capacity": vehicle.get("custom_max_passenger_capacity"),
		"license_plate": vehicle.get("license_plate"),
		"passengers": passengers,
		"joins_elsewhere": [{"accommodation": k, "count": v} for k, v in sorted(joins.items())],
	}


def _paired_returns(trips_rows, shipments, camp_name) -> dict:
	"""(manifest, trip_id) -> {trip_name, trip_time} of the trip carrying the paired Return shipment."""
	pair_of = {}
	for key, rows in trips_rows.items():
		for r in rows:
			s = shipments.get(r.transportation_shipment)
			if r.pickup_accommodation == camp_name and s and s.pair_group and "Outward" in (
				s.trip_direction, s.pre_merge_trip_direction
			):
				pair_of.setdefault(key, (s.name, s.pair_group, rows[0].schedule_date))
				break
	if not pair_of:
		return {}

	partners = {}
	for s in frappe.get_all(
		"Transportation Shipment",
		filters={"pair_group": ["in", list({p[1] for p in pair_of.values()})]},
		fields=["name", "pair_group"],
	):
		partners.setdefault(s.pair_group, []).append(s.name)

	wanted = {name for own, group, _date in pair_of.values() for name in partners.get(group, []) if name != own}
	if not wanted:
		return {}
	Manifest = DocType("Transportation Manifest")
	Detail = DocType("Transportation Manifest Details")
	found = {}
	for r in (
		frappe.qb.from_(Detail)
		.join(Manifest).on(Detail.parent == Manifest.name)
		.select(Detail.transportation_shipment, Manifest.schedule_date, Detail.trip_name, Detail.trip_time)
		.where(Detail.parenttype == "Transportation Manifest")
		.where(Manifest.schedule_date.isin(list({p[2] for p in pair_of.values()})))
		.where(Manifest.docstatus < 2)
		.where(Detail.transportation_shipment.isin(list(wanted)))
		.orderby(Detail.trip_time)
	).run(as_dict=True):
		key = (r.transportation_shipment, getdate(r.schedule_date))
		if key not in found or (r.trip_time and not found[key]["trip_time"]):
			found[key] = {"trip_name": r.trip_name, "trip_time": r.trip_time or None}

	paired = {}
	for key, (own, group, date) in pair_of.items():
		for name in partners.get(group, []):
			if name != own and (name, getdate(date)) in found:
				paired[key] = found[(name, getdate(date))]
				break
	return paired
