import frappe
from collections import defaultdict

MIXED = "Mixed"

# WI-002160: runs merged through the trip picker never reached merge_trip_shipments, so
# they were left un-flagged. This writes what a real merge would have: every assignment
# row MIXED, every shipment Mixed with its own leg kept in pre_merge_trip_direction so
# unmerge_trip_shipment can still restore it. Only runs whose rows genuinely disagree are
# touched.
#
# The shipment's own `trip_group` is deliberately left alone - a real merge fills it with
# merge_key()'s hash, which is not the canvas trip id these rows carry, and nothing reads
# it for logic. Rows are written with db.set_value rather than by saving the plan: saving
# would re-run the whole plan's capacity validation, and a patch must not fail because
# some unrelated lane on a months-old plan no longer passes.


def execute():
	if not frappe.db.exists("DocType", "Route Plan Assignment"):
		return

	rows = frappe.get_all(
		"Route Plan Assignment",
		filters={"trip_group": ["!=", ""]},
		fields=["name", "parent", "vehicle", "trip_group", "direction", "transportation_shipment"],
	)

	runs = defaultdict(list)
	for row in rows:
		if row.vehicle and row.trip_group:
			runs[(row.parent, row.vehicle, row.trip_group)].append(row)

	repaired = 0
	for run in runs.values():
		directions = {(row.direction or "").upper() for row in run}
		# One heading means one plain run; already all MIXED means nothing to do.
		if len(directions) < 2:
			continue

		for row in run:
			if (row.direction or "").upper() != "MIXED":
				frappe.db.set_value(
					"Route Plan Assignment", row.name, "direction", "MIXED", update_modified=False
				)
			_mark_shipment_mixed(row.transportation_shipment)
		repaired += 1

	if repaired:
		# No commit here: the patch runner commits.
		print(f"WI-002160: marked {repaired} un-flagged mixed run(s) as Mixed")


def _mark_shipment_mixed(name):
	"""Record the card's own leg, then flag it Mixed - the order a real merge uses.

	The remembered direction is never overwritten: a card already carrying one was merged
	before, and that original is the one to keep (WI-002071).
	"""
	if not name:
		return

	shipment = frappe.db.get_value(
		"Transportation Shipment",
		name,
		["trip_direction", "pre_merge_trip_direction"],
		as_dict=True,
	)
	if not shipment or shipment.trip_direction == MIXED:
		return

	values = {"trip_direction": MIXED}
	if not shipment.pre_merge_trip_direction:
		values["pre_merge_trip_direction"] = shipment.trip_direction

	frappe.db.set_value("Transportation Shipment", name, values, update_modified=False)
