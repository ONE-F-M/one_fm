# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""Materialize standing Transportation Shipment records from Operations Shift route data.

This is the backend replacement for the on-the-fly card generation that used to
live in the Transportation Schedule page. It reuses the same demand model
(get_grouped_employees_by_accommodation) and the same Direct/OSM/OLM routing
resolution, but persists the result as Transportation Shipment documents so the
canvas can render cards from durable records.

Records are standing (not per-day): a run refreshes the roster of still-Unassigned
shipments, inserts records for new demand, and prunes Unassigned shipments whose
demand has disappeared. Assigned shipments are never touched.
"""

import frappe
from frappe import _
from frappe.utils import get_datetime

from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
	get_coords,
	get_grouped_employees_by_accommodation,
)

# Identity prefix so shift-generated records never collide with Trip Request ones.
GEN_PREFIX = "OPS"
MAHBOULA_LABELS = {"Mahboula 3", "Mahboula 12", "Mahboula 13", "Mahboula 15"}
# Return riders may finish up to an hour after the outbound leg departs.
RETURN_MATCH_FLOOR_SECONDS = -3600


def _minute_of_day(time_val) -> int | None:
	"""Seconds-since-midnight for a Time value, used for return-rider matching."""
	if not time_val:
		return None
	try:
		dt = get_datetime(f"2000-01-01 {time_val}")
		return dt.hour * 3600 + dt.minute * 60 + dt.second
	except Exception:
		return None


def build_demand_descriptors(nested_map: dict) -> list:
	"""Turn the accommodation->shift->employees map into round-trip demand descriptors.

	Returns a list of base demands (one per Direct/OSM/OLM grouping) with the
	going roster and a cross-referenced return roster attached. Direction-specific
	records are expanded later in generate_transportation_shipments().
	"""
	if not nested_map:
		return []

	# ── Batch employee labels ──
	all_emp_ids = set()
	for acc_data in nested_map.values():
		for emp_list in acc_data["shifts"].values():
			all_emp_ids.update(emp_list)

	emp_name_map = {}
	if all_emp_ids:
		for e in frappe.get_all(
			"Employee",
			filters={"name": ["in", list(all_emp_ids)]},
			fields=["name", "employee_name", "cell_number", "site"],
		):
			emp_name_map[e.name] = e

	def emp_obj(emp_id):
		info = emp_name_map.get(emp_id)
		return {
			"id": emp_id,
			"name": (info.employee_name if info else emp_id) or emp_id,
			"mobile": (info.cell_number if info else "") or "",
			"site": (info.site if info else None),
		}

	# ── Batch shift docs ──
	all_shift_names = set()
	for acc_data in nested_map.values():
		all_shift_names.update(acc_data["shifts"].keys())

	shift_doc_map = {}
	if all_shift_names:
		for s in frappe.get_all(
			"Operations Shift",
			filters={"name": ["in", list(all_shift_names)]},
			fields=["name", "site", "start_time", "end_time", "expected_arrival_time_at_site"],
		):
			shift_doc_map[s.name] = s

	# ── Batch site locations ──
	all_sites = list({s.site for s in shift_doc_map.values() if s.site})
	site_location_map = {}
	if all_sites:
		for row in frappe.get_all(
			"Operations Site",
			filters={"name": ["in", all_sites]},
			fields=["name", "site_location"],
		):
			site_location_map[row.name] = row.site_location or row.name

	# ── OSM stop locations per site ──
	osm_by_site = {}
	if all_sites:
		osm_records = frappe.get_all(
			"Site Transport Stop Location",
			filters={"site_arrangement": "One Site Many Locations", "site": ["in", all_sites]},
			fields=["name", "site"],
		)
		if osm_records:
			osm_site_lookup = {r.name: r.site for r in osm_records}
			for child in frappe.get_all(
				"Site To Location Mapping",
				filters={"parent": ["in", [r.name for r in osm_records]]},
				fields=["parent", "location"],
			):
				site = osm_site_lookup.get(child.parent)
				if site and child.location:
					osm_by_site.setdefault(site, []).append(child.location)

	# ── OLM parents per site ──
	olm_by_site = {}
	olm_doc_map = {}
	if all_sites:
		olm_child_rows = frappe.get_all(
			"Location To Site Mapping",
			filters={"parenttype": "Site Transport Stop Location", "sites": ["in", all_sites]},
			fields=["parent", "sites"],
		)
		olm_parent_names = set()
		for child in olm_child_rows:
			olm_by_site.setdefault(child.sites, []).append(child.parent)
			olm_parent_names.add(child.parent)
		if olm_parent_names:
			for doc in frappe.get_all(
				"Site Transport Stop Location",
				filters={"name": ["in", list(olm_parent_names)], "site_arrangement": "One Location Many Sites"},
				fields=["name", "transport_stop_location"],
			):
				olm_doc_map[doc.name] = doc

	# ── Build base demands per accommodation ──
	demands = []

	for acc_name, acc_data in nested_map.items():
		lookup_id = acc_data["lookup_id"]
		if not get_coords("Accommodation", lookup_id):
			continue

		olm_groups = {}

		for shift_name, employee_list in acc_data["shifts"].items():
			shift_doc = shift_doc_map.get(shift_name)
			if not shift_doc:
				continue

			operations_site = shift_doc.site
			headcount = len(employee_list)
			handled = False

			# ── OSM: one demand per stop location, employees round-robin ──
			osm_locations = [loc for loc in osm_by_site.get(operations_site, []) if get_coords("Location", loc)]
			if osm_locations:
				handled = True
				num_locs = len(osm_locations)
				base_h = headcount // num_locs
				extra_h = headcount % num_locs
				emp_idx = 0
				for i, loc in enumerate(osm_locations):
					current_h = base_h + (1 if i < extra_h else 0)
					loc_emps = employee_list[emp_idx:emp_idx + current_h]
					emp_idx += current_h
					if not current_h:
						continue
					demands.append({
						"acc_name": acc_name,
						"accommodation": lookup_id,
						"operations_shift": shift_name,
						"operations_site": operations_site,
						"stop_location": loc,
						"routing": "OSM",
						"group_token": shift_name,
						"start_time": shift_doc.start_time,
						"end_time": shift_doc.end_time,
						"employees": [emp_obj(e) for e in loc_emps],
					})

			# ── OLM: aggregate across shifts by (stop_location, hour) ──
			for parent_name in olm_by_site.get(operations_site, []):
				olm_doc = olm_doc_map.get(parent_name)
				if not olm_doc or not olm_doc.transport_stop_location:
					continue
				handled = True
				stop_location = olm_doc.transport_stop_location
				start_dt = get_datetime(f"2000-01-01 {shift_doc.start_time}") if shift_doc.start_time else None
				time_key = start_dt.hour if start_dt else 0
				group_key = (stop_location, time_key)
				grp = olm_groups.setdefault(group_key, {
					"shifts": [], "employees": [], "start": shift_doc.start_time, "end": shift_doc.end_time,
				})
				grp["shifts"].append(shift_name)
				grp["employees"].extend(employee_list)
				if shift_doc.start_time and (not grp["start"] or shift_doc.start_time < grp["start"]):
					grp["start"] = shift_doc.start_time
				if shift_doc.end_time and (not grp["end"] or shift_doc.end_time > grp["end"]):
					grp["end"] = shift_doc.end_time

			# ── Direct fallback ──
			if not handled:
				site_loc = site_location_map.get(operations_site)
				if site_loc and get_coords("Location", site_loc):
					demands.append({
						"acc_name": acc_name,
						"accommodation": lookup_id,
						"operations_shift": shift_name,
						"operations_site": operations_site,
						"stop_location": site_loc,
						"routing": "Direct",
						"group_token": shift_name,
						"start_time": shift_doc.start_time,
						"end_time": shift_doc.end_time,
						"employees": [emp_obj(e) for e in employee_list],
					})

		# ── Emit aggregated OLM demands for this accommodation ──
		for (stop_location, time_key), grp in olm_groups.items():
			if not get_coords("Location", stop_location):
				continue
			demands.append({
				"acc_name": acc_name,
				"accommodation": lookup_id,
				"operations_shift": None,
				"operations_site": None,
				"stop_location": stop_location,
				"routing": "OLM",
				"group_token": f"GROUP-{time_key}",
				"start_time": grp["start"],
				"end_time": grp["end"],
				"employees": [emp_obj(e) for e in grp["employees"]],
			})

	_attach_return_rosters(demands)
	return demands


def _attach_return_rosters(demands: list) -> None:
	"""For each demand, find the finishing-shift roster at the same stop/accommodation.

	Mirrors the return-rider cross-reference in get_route_planner_data: same stop
	location, same accommodation, a different shift whose end time sits closest to
	(and not long after) this demand's start time.
	"""
	by_stop = {}
	for d in demands:
		by_stop.setdefault(d["stop_location"], []).append(d)

	for d in demands:
		start_s = _minute_of_day(d["start_time"])
		d["return_employees"] = []
		if start_s is None:
			continue

		best, best_gap = None, float("inf")
		for other in by_stop.get(d["stop_location"], []):
			if other is d or other["group_token"] == d["group_token"]:
				continue
			if other["acc_name"] != d["acc_name"]:
				continue
			end_s = _minute_of_day(other["end_time"])
			if end_s is None:
				continue
			diff = start_s - end_s
			if diff >= RETURN_MATCH_FLOOR_SECONDS and abs(diff) < best_gap:
				best_gap = abs(diff)
				best = other

		if best:
			d["return_employees"] = best["employees"]


def _generation_key(demand: dict, direction: str) -> tuple:
	"""Return (generation_key, pair_group) for a demand+direction."""
	pair = f"{GEN_PREFIX}|{demand['accommodation']}|{demand['group_token']}|{demand['stop_location']}|{demand['routing']}"
	return f"{pair}|{direction}", pair


def _write_shipment(doc, demand: dict, direction: str, roster: list, gen_key: str, pair_group: str) -> None:
	"""Set header + child roster on a new or existing shipment document."""
	doc.accommodation = demand["accommodation"]
	doc.operations_shift = demand["operations_shift"]
	doc.operations_site = demand["operations_site"]
	doc.stop_location = demand["stop_location"]
	doc.routing_type_badge = demand["routing"]
	doc.trip_direction = direction
	doc.start_time = demand["start_time"]
	doc.end_time = demand["end_time"]
	doc.headcount = len(roster)
	doc.source_doctype = "Operations Shift"
	doc.source_docname = demand["operations_shift"]  # blank for aggregated OLM
	doc.is_adhoc_journey = 0
	doc.generation_key = gen_key
	doc.pair_group = pair_group

	doc.set("transportation_shipment_employee", [])
	for emp in roster:
		doc.append("transportation_shipment_employee", {
			"employee_id": emp["id"],
			"employee_name": emp["name"],
			"cell_number": emp["mobile"],
			"accommodation": demand["accommodation"],
			"stop_location": demand["stop_location"],
			"operation_site": demand["operations_site"] or emp.get("site"),
		})


@frappe.whitelist()
def generate_transportation_shipments():
	"""Idempotently materialize/refresh Transportation Shipment records.

	Entry point for both the daily scheduler and the canvas "Generate" button.
	Returns a summary dict of what changed.
	"""
	# The scheduler runs as Administrator; guard interactive/API calls.
	if frappe.session.user != "Administrator":
		frappe.only_for("System Manager")

	nested_map = get_grouped_employees_by_accommodation()
	demands = build_demand_descriptors(nested_map)

	created = updated = deleted = errors = 0
	current_keys = set()

	for demand in demands:
		for direction in ("Outward", "Return"):
			try:
				roster = demand["employees"] if direction == "Outward" else (
					demand.get("return_employees") or demand["employees"]
				)
				if not roster:
					continue

				gen_key, pair_group = _generation_key(demand, direction)
				current_keys.add(gen_key)

				existing = frappe.db.get_value(
					"Transportation Shipment", {"generation_key": gen_key}, ["name", "status"], as_dict=True
				)

				if not existing:
					doc = frappe.new_doc("Transportation Shipment")
					doc.status = "Unassigned"
					_write_shipment(doc, demand, direction, roster, gen_key, pair_group)
					doc.insert(ignore_permissions=True)
					created += 1
				elif existing.status == "Unassigned":
					doc = frappe.get_doc("Transportation Shipment", existing.name)
					_write_shipment(doc, demand, direction, roster, gen_key, pair_group)
					doc.save(ignore_permissions=True)
					updated += 1
				# Assigned → leave untouched
			except Exception:
				errors += 1
				frappe.log_error(frappe.get_traceback(), "Transportation Shipment Generation Error")

	deleted = _prune_stale(current_keys)

	frappe.db.commit()
	summary = {"created": created, "updated": updated, "deleted": deleted, "errors": errors}
	frappe.logger().info(f"generate_transportation_shipments: {summary}")
	return summary


def _prune_stale(current_keys: set) -> int:
	"""Delete Unassigned shift-generated shipments whose demand disappeared."""
	stale = frappe.get_all(
		"Transportation Shipment",
		filters={"source_doctype": "Operations Shift", "status": "Unassigned"},
		fields=["name", "generation_key"],
	)
	deleted = 0
	for row in stale:
		if row.generation_key and row.generation_key not in current_keys:
			try:
				frappe.delete_doc("Transportation Shipment", row.name, ignore_permissions=True, force=True)
				deleted += 1
			except Exception:
				frappe.log_error(frappe.get_traceback(), "Transportation Shipment Prune Error")
	return deleted
