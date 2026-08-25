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
from frappe.utils import get_datetime, getdate, today

from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
	get_coords,
	get_grouped_employees_by_accommodation,
)

# Identity prefix so shift-generated records never collide with Trip Request ones.
GEN_PREFIX = "OPS"
# Identity prefix for shipments split out of a single Trip Request by camp.
TRQ_PREFIX = "TRQ"
TRIP_REQUEST = "Trip Request"
# Retention-based card conversion (MA-10) is a Company Fleet concern only; other
# transportation methods are handled off the fleet scheduling canvas.
COMPANY_FLEET = "Company Fleet"
MAHBOULA_LABELS = {"Mahboula 3", "Mahboula 12", "Mahboula 13", "Mahboula 15"}
# Return riders may finish up to an hour after the outbound leg departs.
RETURN_MATCH_FLOOR_SECONDS = -3600
# Who may refresh the shipment cards from the canvas (WI-002162).
GENERATE_ROLES = ("System Manager", "Transportation Manager", "Transportation Supervisor")


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
	# The scheduler runs as Administrator; guard interactive/API calls. The button
	# lives on the Transportation Schedule canvas, which is the transport team's own
	# board, so the roles that run it may refresh their own cards (WI-002162) instead
	# of having to ask a System Manager.
	if frappe.session.user != "Administrator":
		frappe.only_for(GENERATE_ROLES)

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


# ─────────────────────────────────────────────────────────────────────────────
# Trip Request → per-camp shipment split (MA 5 - 4)
#
# A single multi-passenger Trip Request can list workers who live in different
# camps. The scheduling canvas needs demand grouped by true physical origin, so
# a Trip Request is fragmented into one Outward + one Return shipment PER camp,
# clustered strictly by the passenger's accommodation_camp, spanning the whole
# from_date→to_date duration block (a standing card, not one per day).
# ─────────────────────────────────────────────────────────────────────────────


def _card_directions(vehicle_retention) -> tuple:
	"""Directions to materialize per camp for a Company Fleet Trip Request (MA-10).

	Vehicle Retention ON collapses the round trip into a single combined Outward
	card (drop-off + immediate return leg); OFF keeps separate Outward and Return
	master cards.
	"""
	return ("Outward",) if vehicle_retention else ("Outward", "Return")


def _trip_request_generation_key(trip_request: str, camp: str, direction: str) -> tuple:
	"""Return (generation_key, pair_group) for a Trip Request camp cluster.

	pair_group is shared by the Outward and Return records of the same camp so
	the canvas can pair them; generation_key adds the direction for idempotency.
	"""
	pair = f"{TRQ_PREFIX}|{trip_request}|{camp}"
	return f"{pair}|{direction}", pair


def _group_passengers_by_camp(trip_request_doc) -> dict:
	"""Cluster a Trip Request's passengers strictly by accommodation_camp.

	Returns an ordered {camp: [passenger_row, ...]} map. Passengers with no
	accommodation_camp are skipped — they have no physical origin to group by,
	so they cannot be materialized as a camp-origin demand card.
	"""
	groups = {}
	for passenger in trip_request_doc.transport_request_passenger:
		camp = passenger.accommodation_camp
		if not camp:
			continue
		groups.setdefault(camp, []).append(passenger)
	return groups


def _write_trip_request_shipment(doc, trip_request_doc, camp, passengers, direction, gen_key, pair_group):
	"""Set header + camp roster on a new or existing Trip Request shipment.

	Header fields the controller does not derive are set here; stop_location,
	per-row routing and headcount are left to the Transportation Shipment
	controller (apply_trip_request_rules / apply_routing_type / calculate_headcount),
	which runs on save and reuses the exact ad-hoc Trip Request rules.
	"""
	doc.source_doctype = TRIP_REQUEST
	doc.source_docname = trip_request_doc.name
	doc.accommodation = camp
	doc.trip_direction = direction
	# Camp → destination is a point-to-point ad-hoc journey.
	doc.routing_type_badge = "Direct"
	doc.is_adhoc_journey = 1
	doc.requires_vehicle_retention = 1 if trip_request_doc.vehicle_retention else 0
	# Times come from the Trip Request; the whole duration block is one card.
	doc.start_time = trip_request_doc.departure_time
	doc.end_time = trip_request_doc.return_time
	doc.from_date = trip_request_doc.from_date
	doc.to_date = trip_request_doc.to_date
	doc.generation_key = gen_key
	doc.pair_group = pair_group

	doc.set("transportation_shipment_employee", [])
	for passenger in passengers:
		# The controller's Direct routing fills accommodation/stop_location/operation_site
		# uniformly from the header, so only the rider identity is set here.
		doc.append("transportation_shipment_employee", {
			"employee_id": passenger.employee_id,
			"employee_name": passenger.employee_name,
		})


def generate_shipments_from_trip_request(trip_request) -> dict:
	"""Split one Trip Request into per-camp shipment cards, retention-aware (MA-10).

	Only Company Fleet trips produce cards; any other transportation method yields
	nothing (and prunes stale Unassigned cards, so amending the method away from
	Company Fleet cleans up). For a Company Fleet trip, Vehicle Retention decides
	how many cards each camp cluster becomes:

	- Retention ON  → a single combined Outward card per camp covering both the
	  drop-off and the immediate return leg (short window / turnaround).
	- Retention OFF → separate Outward and Return master cards per camp (two),
	  for independent daily drops and pickups.

	Idempotent: re-running (e.g. on amend) refreshes still-Unassigned cards and
	prunes Unassigned cards for camps/directions no longer on the request, but
	never touches cards already Assigned to a Route Plan. So flipping retention on
	prunes the now-orphaned Return card, and flipping it off recreates it. Returns
	a summary of what changed.
	"""
	trip_request_doc = (
		trip_request if hasattr(trip_request, "transport_request_passenger")
		else frappe.get_doc(TRIP_REQUEST, trip_request)
	)

	# Non-Company-Fleet trips have no fleet cards; prune any left from a prior
	# submit/amend so switching method away from Company Fleet clears the canvas.
	if trip_request_doc.transportation_method != COMPANY_FLEET:
		deleted = remove_unassigned_shipments_for_trip_request(trip_request_doc.name)
		summary = {"created": 0, "updated": 0, "deleted": deleted, "errors": 0}
		frappe.logger().info(
			f"generate_shipments_from_trip_request[{trip_request_doc.name}]: "
			f"method={trip_request_doc.transportation_method} (skipped) {summary}"
		)
		return summary

	# Vehicle Retention collapses the round trip into one combined Outward card.
	directions = _card_directions(trip_request_doc.vehicle_retention)

	groups = _group_passengers_by_camp(trip_request_doc)

	created = updated = deleted = errors = 0
	current_keys = set()

	for camp, passengers in groups.items():
		for direction in directions:
			try:
				gen_key, pair_group = _trip_request_generation_key(
					trip_request_doc.name, camp, direction
				)
				current_keys.add(gen_key)

				existing = frappe.db.get_value(
					"Transportation Shipment", {"generation_key": gen_key},
					["name", "status"], as_dict=True,
				)

				if not existing:
					doc = frappe.new_doc("Transportation Shipment")
					doc.status = "Unassigned"
					_write_trip_request_shipment(
						doc, trip_request_doc, camp, passengers, direction, gen_key, pair_group
					)
					doc.insert(ignore_permissions=True)
					created += 1
				elif existing.status == "Unassigned":
					doc = frappe.get_doc("Transportation Shipment", existing.name)
					_write_trip_request_shipment(
						doc, trip_request_doc, camp, passengers, direction, gen_key, pair_group
					)
					doc.save(ignore_permissions=True)
					updated += 1
				# Assigned → leave untouched
			except Exception:
				errors += 1
				frappe.log_error(frappe.get_traceback(), "Trip Request Shipment Split Error")

	deleted = _prune_stale_for_trip_request(trip_request_doc.name, current_keys)

	summary = {"created": created, "updated": updated, "deleted": deleted, "errors": errors}
	frappe.logger().info(f"generate_shipments_from_trip_request[{trip_request_doc.name}]: {summary}")
	return summary


def _prune_stale_for_trip_request(trip_request: str, current_keys: set) -> int:
	"""Delete Unassigned camp cards of this Trip Request that no longer apply.

	Scoped to the one Trip Request so it never touches shipments from other Trip
	Requests or from the Operations Shift generator.
	"""
	stale = frappe.get_all(
		"Transportation Shipment",
		filters={
			"source_doctype": TRIP_REQUEST,
			"source_docname": trip_request,
			"status": "Unassigned",
		},
		fields=["name", "generation_key"],
	)
	deleted = 0
	for row in stale:
		if row.generation_key and row.generation_key not in current_keys:
			try:
				frappe.delete_doc("Transportation Shipment", row.name, ignore_permissions=True, force=True)
				deleted += 1
			except Exception:
				frappe.log_error(frappe.get_traceback(), "Trip Request Shipment Prune Error")
	return deleted


def remove_unassigned_shipments_for_trip_request(trip_request: str) -> int:
	"""Delete all still-Unassigned camp cards of a Trip Request (used on cancel).

	Assigned cards are left in place so a cancelled request does not silently
	pull a shipment out from under a Route Plan that already placed it.
	"""
	return _prune_stale_for_trip_request(trip_request, current_keys=set())


# ─────────────────────────────────────────────────────────────────────────────
# Expiry engine (TR 3 - 9)
#
# A multi-day shipment card is only relevant while its event is still running.
# Once the system date crosses the card's to_date (end date), the card is stale
# and must leave the canvas workspace. We flip its status to "Inactive" rather
# than delete it, so the record is preserved for reporting/audit while the canvas
# (which only renders Unassigned + Assigned cards) stops showing it.
# ─────────────────────────────────────────────────────────────────────────────


def deactivate_expired_shipments(as_of: str | None = None) -> int:
	"""Flag shipments whose event window has passed as Inactive.

	Daily scheduler entry point covering both pools:
	- ``Unassigned`` cards expire the day after their own ``to_date``. Standing
	  Operations Shift cards carry no to_date and are never affected (AC2).
	- ``Assigned`` cards (placed on a vehicle) expire once their Route Plan lock
	  window has ended — see ``_expired_assigned_shipments`` — so the block leaves
	  the canvas after the dispatcher's lock End Date (TR-8, AC1). The vehicle
	  frees automatically because the lock-overlap check ignores ended windows.

	Returns the number of shipments deactivated.
	"""
	cutoff_date = getdate(as_of or today())

	# Unassigned cards expire on their own to_date. Blank Date fields can land as
	# NULL or '0000-00-00' in the DB, and the latter slips past a plain SQL
	# "< cutoff" filter, so we re-check in Python with getdate() to reliably
	# exclude standing (undated) cards.
	expired = set()
	for row in frappe.get_all(
		"Transportation Shipment",
		filters={"status": "Unassigned"},
		fields=["name", "to_date"],
	):
		if row.to_date and getdate(row.to_date) < cutoff_date:
			expired.add(row.name)

	# Assigned cards expire once their Route Plan lock window has fully ended.
	expired |= _expired_assigned_shipments(cutoff_date)

	count = 0
	for name in expired:
		try:
			frappe.db.set_value("Transportation Shipment", name, "status", "Inactive")
			count += 1
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Transportation Shipment Expiry Error")

	if count:
		frappe.db.commit()

	frappe.logger().info(f"deactivate_expired_shipments[{cutoff_date}]: deactivated {count}")
	return count


def _expired_assigned_shipments(cutoff_date) -> set:
	"""Return Assigned shipments whose Route Plan lock window has fully ended.

	Each placement's lock lifespan lives in the DATE part of the Route Plan
	Assignment ``start_time``/``end_time`` (the TIME part is the daily trip
	window). The lock end — the DATE the dispatcher set in the canvas modal — is
	authoritative here, mirroring the canvas display gate:

	- A placement is **bounded** when its assignment spans more than one day
	  (``end date > start date``) OR the shipment carries a ``to_date``. It
	  expires once every assignment that references it ends before ``cutoff_date``.
	- A placement is **continuous** (single-day span AND no ``to_date``) and never
	  expires (AC2).
	- An Assigned shipment referenced by no plan row falls back to its own
	  ``to_date``.
	"""
	assigned = frappe.get_all(
		"Transportation Shipment",
		filters={"status": "Assigned"},
		fields=["name", "to_date"],
	)
	if not assigned:
		return set()

	to_date_by = {row.name: row.to_date for row in assigned}

	rows_by = {}
	for r in frappe.get_all(
		"Route Plan Assignment",
		filters={"transportation_shipment": ["in", list(to_date_by)]},
		fields=["transportation_shipment", "start_time", "end_time"],
	):
		rows_by.setdefault(r.transportation_shipment, []).append(r)

	expired = set()
	for name, to_date in to_date_by.items():
		rows = rows_by.get(name)
		if not rows:
			# Assigned but no plan row references it — fall back to its to_date.
			if to_date and getdate(to_date) < cutoff_date:
				expired.add(name)
			continue

		ends, is_multiday, parseable = [], False, True
		for r in rows:
			start_date = getdate(str(r.start_time)[:10]) if r.start_time else None
			end_date = getdate(str(r.end_time)[:10]) if r.end_time else None
			if end_date is None:
				parseable = False  # a blank/unparseable end keeps the card live
				break
			ends.append(end_date)
			if start_date and end_date > start_date:
				is_multiday = True

		if not parseable:
			continue

		# Single-day placements with no to_date are open-ended runs — never expire.
		if not is_multiday and not to_date:
			continue

		if max(ends) < cutoff_date:
			expired.add(name)

	return expired
