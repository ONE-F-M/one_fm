import frappe
from collections import defaultdict

MIXED = "Mixed"

# WI-002160: a run that both drops off and picks up is a Mixed trip, but only the Merge
# Trip modal ever wrote that down. Chaining a return stop onto an outbound run through the
# "Add Stop to which trip?" picker skipped the modal entirely, so the run kept every stop
# on its original heading and no card recorded pre_merge_trip_direction. The canvas now
# reads a run's direction from its stops rather than from the flag, so the seat maths is
# right either way — but the stored data still says two things at once: the block draws in
# the first stop's colour, and the shipments describe journeys the plan is no longer
# running them on.
#
# This brings those runs up to what a real merge would have written:
#
#   * every assignment row of the run reads MIXED;
#   * every shipment on it reads Mixed, with its own leg preserved in
#     pre_merge_trip_direction so unmerge_trip_shipment can put it back when the card
#     leaves the run.
#
# Only runs whose rows genuinely disagree about direction are touched. A single-direction
# multi-stop run is not a merge and is left exactly as it is.
#
# `trip_group` on the shipment is deliberately not written. A real merge fills it with
# merge_key()'s hash of the shipment names, which is a different thing from the canvas
# trip id these rows carry, and nothing reads the shipment's copy for logic — only the
# merge endpoint's return value is consumed, and that is not in play here.
#
# Rows are written with db.set_value rather than by saving the Route Plan: saving would
# re-run the whole plan's capacity validation, and a patch must not fail because some
# unrelated lane on a months-old plan no longer passes.


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
		# No commit here: the patch runner commits, and committing inside would break
		# the transaction a test wraps this in.
		print(f"WI-002160: marked {repaired} un-flagged mixed run(s) as Mixed")


def _mark_shipment_mixed(name):
	"""Record the card's own leg, then flag it Mixed — the order a real merge uses.

	Writing Mixed without first remembering the original is what stranded cards as Mixed
	for good in WI-002071, so the remembered direction is set first and never overwritten:
	a card already carrying one was merged before and its original is the one to keep.
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
