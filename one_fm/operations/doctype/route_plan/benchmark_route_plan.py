# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""Measure the Transportation Schedule board on a Route Plan, and dump what the daily jobs build.

Run these on a LOCAL site restored from a production backup, never on production.

Board timings (median of ``runs``; the save is rolled back every time):

	bench execute one_fm.operations.doctype.route_plan.benchmark_route_plan.run
	bench execute one_fm.operations.doctype.route_plan.benchmark_route_plan.run --kwargs "{'plan': 'RP-2026-06-1754678', 'runs': 10}"

run() calls only the two whitelisted page methods, load_assignments and save_assignments,
so the same file runs unchanged on the code before and after the Route Plan Assignment
change. For the "before" numbers copy this file onto that checkout.

Daily-job outputs (shipments and today's manifests, sorted, as JSON):

	bench execute one_fm.operations.doctype.route_plan.benchmark_route_plan.snapshot_outputs --kwargs "{'path': '/tmp/rpa-before.json'}"

This RUNS generate_transportation_shipments and compile_daily_manifests and keeps what they
write. Restore the same backup, migrate, run it again on the same calendar day into another
file and diff the two.

A plan ten times the size of the default one, for the scale comparison:

	bench execute one_fm.operations.doctype.route_plan.benchmark_route_plan.make_synthetic_plan --kwargs "{'rows': 10000}"

It needs the standalone Route Plan Assignment, so it only runs after the change. It prints
the new plan's name; pass that to run(), then remove it:

	bench execute one_fm.operations.doctype.route_plan.benchmark_route_plan.drop_synthetic_plan --kwargs "{'plan': 'RP-...'}"
"""

import json
import math
import statistics
import time
from contextlib import contextmanager

import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime


@contextmanager
def _query_counter():
	"""Count frappe.db.sql calls, the way FrappeTestCase.assertQueryCount does."""
	count = [0]
	original = frappe.db.__class__.sql

	def counted(self, *args, **kwargs):
		count[0] += 1
		return original(self, *args, **kwargs)

	frappe.db.__class__.sql = counted
	try:
		yield count
	finally:
		frappe.db.__class__.sql = original


def _default_plan():
	return frappe.db.get_value("Route Plan", {"is_default": 1}, "name") or frappe.db.get_value(
		"Route Plan", {"status": "Active"}, "name"
	)


def _moved_five_minutes(items):
	"""The loaded board with the first timed card's start moved by five minutes."""
	for item in items:
		if item.get("start"):
			start = get_datetime(str(item["start"]).replace("T", " ").replace("Z", "").split(".")[0])
			item["start"] = add_to_date(start, minutes=5).strftime("%Y-%m-%dT%H:%M:%S.000Z")
			return items
	return items


def run(plan=None, runs=10) -> dict:
	"""Median load time (server side), payload size, load queries and one-card save time."""
	from one_fm.one_fm.page.transportation_schedule.transportation_schedule import (
		load_assignments,
		save_assignments,
	)

	plan = plan or _default_plan()
	load_seconds, sizes, queries, save_seconds = [], [], [], []
	for _ in range(int(runs)):
		with _query_counter() as count:
			started = time.perf_counter()
			result = load_assignments(plan)
			load_seconds.append(time.perf_counter() - started)
		queries.append(count[0])
		sizes.append(len(frappe.as_json(result)))

		frappe.db.savepoint("route_plan_benchmark")
		started = time.perf_counter()
		save_assignments(
			plan,
			json.dumps(_moved_five_minutes(result["swim_items"]), default=str),
			json.dumps(result["assigned_cards"]),
			json.dumps(result["leg_timings"], default=str),
		)
		save_seconds.append(time.perf_counter() - started)
		frappe.db.rollback(save_point="route_plan_benchmark")

	medians = {
		"plan": plan,
		"rows": frappe.db.count("Route Plan Assignment", {"route_plan": plan})
		if frappe.db.has_column("Route Plan Assignment", "route_plan")
		else frappe.db.count("Route Plan Assignment", {"parent": plan}),
		"runs": int(runs),
		"load_seconds": round(statistics.median(load_seconds), 4),
		"payload_bytes": int(statistics.median(sizes)),
		"load_queries": int(statistics.median(queries)),
		"save_one_card_seconds": round(statistics.median(save_seconds), 4),
	}
	print(json.dumps(medians, indent=1))
	return medians


def snapshot_outputs(path) -> None:
	"""Run the daily shipment and manifest jobs and dump what they produced, sorted."""
	from one_fm.one_fm.doctype.transportation_manifest.manifest_compiler import (
		compile_daily_manifests,
	)
	from one_fm.one_fm.doctype.transportation_shipment.shipment_generator import (
		generate_transportation_shipments,
	)

	generate_transportation_shipments()
	compile_daily_manifests()

	riders = {}
	for row in frappe.get_all(
		"Transportation Shipment Employee",
		filters={"parenttype": "Transportation Shipment"},
		fields=["parent", "employee_id"],
	):
		riders.setdefault(row.parent, []).append(row.employee_id)
	shipments = sorted(
		(
			{
				"generation_key": row.generation_key,
				"status": row.status,
				"headcount": row.headcount,
				"trip_direction": row.trip_direction,
				"employees": sorted(riders.get(row.name, [])),
			}
			for row in frappe.get_all(
				"Transportation Shipment",
				fields=["name", "generation_key", "status", "headcount", "trip_direction"],
			)
		),
		key=lambda row: json.dumps(row, sort_keys=True, default=str),
	)

	today = now_datetime().date()
	manifests = frappe.get_all(
		"Transportation Manifest", filters={"schedule_date": today},
		fields=["name", "vehicle_no", "schedule_date"],
	)
	details = {}
	for row in frappe.get_all(
		"Transportation Manifest Details",
		filters={"parent": ["in", [m.name for m in manifests] or [""]]},
		fields=["parent", "employee", "stop_sequence", "employee_action"],
	):
		details.setdefault(row.parent, []).append(
			{"employee": row.employee, "stop_sequence": row.stop_sequence, "action": row.employee_action}
		)
	manifest_rows = sorted(
		(
			{
				"vehicle_no": m.vehicle_no,
				"schedule_date": str(m.schedule_date),
				"details": sorted(details.get(m.name, []), key=lambda d: json.dumps(d, sort_keys=True, default=str)),
			}
			for m in manifests
		),
		key=lambda row: json.dumps(row, sort_keys=True, default=str),
	)

	with open(path, "w") as out:
		json.dump({"shipments": shipments, "manifests": manifest_rows}, out, indent=1, sort_keys=True, default=str)
	print(f"{len(shipments)} shipment(s), {len(manifest_rows)} manifest(s) written to {path}")


def make_synthetic_plan(rows=10000, source=None) -> str:
	"""A Draft plan of about ``rows`` assignments cloned from ``source`` (default plan).

	Each copy gets its own vehicles (bulk-inserted VHL-SYN-<copy>-<n>), because a plan ten
	times the size has ten times the buses, not ten times the trips on each bus. Card ids
	and trip groups get a per-copy prefix; shipments stay linked, so live headcounts and
	names are read the same way as on the real plan.
	"""
	from one_fm.operations.doctype.route_plan.route_plan import get_plan_rows, plan_row_fields

	source = source or _default_plan()
	source_rows = get_plan_rows(source)
	if not source_rows:
		frappe.throw(f"Route Plan {source} has no assignments to clone")
	copies = math.ceil(int(rows) / len(source_rows))

	plan = frappe.get_doc({
		"doctype": "Route Plan",
		"title": f"Synthetic {rows} {frappe.generate_hash(length=6)}",
		"status": "Draft",
		"effective_from": now_datetime().date(),
	}).insert(ignore_permissions=True)

	now = now_datetime()
	audit = {"creation": now, "modified": now, "owner": "Administrator", "modified_by": "Administrator"}

	vehicle_fields = [
		f for f in ("seats", "custom_includes_driver_seat", "custom_max_passenger_capacity",
					"location", "make", "model", "one_fm_vehicle_type", "one_fm_vehicle_category")
		if frappe.db.has_column("Vehicle", f)
	]
	sources = {
		v.name: v for v in frappe.get_all(
			"Vehicle", filters={"name": ["in", list({r.vehicle for r in source_rows})]},
			fields=["name"] + vehicle_fields,
		)
	}
	vehicle_of, vehicles = {}, []
	for copy in range(copies):
		for n, name in enumerate(sorted(sources), start=1):
			clone = f"VHL-SYN-{copy:02d}-{n:03d}"
			vehicle_of[(copy, name)] = clone
			if not frappe.db.exists("Vehicle", clone):
				vehicles.append([clone, clone] + [sources[name].get(f) for f in vehicle_fields] + list(audit.values()))
	if vehicles:
		frappe.db.bulk_insert(
			"Vehicle", fields=["name", "license_plate"] + vehicle_fields + list(audit), values=vehicles
		)

	fields = [f for f in plan_row_fields() if f not in ("name", "modified", "route_plan", "idx")]
	values, idx = [], 0
	for copy in range(copies):
		# The first copy keeps the real card ids, so the card run() moves is still read as
		# its own shipment and a save is judged as it is on the real plan. A prefixed id
		# no longer names a shipment, which counts as a new card on its run.
		prefix = f"SYN{copy:02d}-" if copy else ""
		for row in source_rows:
			idx += 1
			if idx > int(rows):
				break
			clone = dict(row)
			if clone.get("is_camp_leg") and "|" in str(clone.get("card_id")):
				head, group, stop = str(clone["card_id"]).split("|", 2)
				clone["card_id"] = f"{head}|{prefix}{group}|{stop}"
			else:
				clone["card_id"] = f"{prefix}{clone['card_id']}"
			if clone.get("trip_group"):
				clone["trip_group"] = f"{prefix}{clone['trip_group']}"
			clone["vehicle"] = vehicle_of.get((copy, row.vehicle), row.vehicle)
			values.append(
				[frappe.generate_hash(length=10), plan.name, idx]
				+ [clone.get(f) for f in fields]
				+ list(audit.values())
			)
	frappe.db.bulk_insert(
		"Route Plan Assignment",
		fields=["name", "route_plan", "idx"] + fields + list(audit),
		values=values,
		chunk_size=2000,
	)
	print(f"{plan.name}: {len(values)} assignment(s) on {len(vehicles)} new vehicle(s)")
	return plan.name


def drop_synthetic_plan(plan) -> None:
	"""Remove a plan made by make_synthetic_plan and the VHL-SYN vehicles no plan uses."""
	frappe.db.delete("Route Plan Assignment", {"route_plan": plan})
	frappe.db.delete("Route Plan", {"name": plan})
	used = set(frappe.get_all("Route Plan Assignment", filters={"vehicle": ["like", "VHL-SYN-%"]},
							  pluck="vehicle", distinct=True))
	unused = [v for v in frappe.get_all("Vehicle", filters={"name": ["like", "VHL-SYN-%"]}, pluck="name")
			  if v not in used]
	if unused:
		frappe.db.delete("Vehicle", {"name": ["in", unused]})
	print(f"{plan} removed with {len(unused)} synthetic vehicle(s)")
