# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

"""Read-only endpoints for the manifest page's camp filter and departure slots."""

import frappe
from frappe.query_builder import DocType
from frappe.utils import getdate, today


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
