import frappe
from frappe.utils import getdate, nowdate

# A run moved whole onto another vehicle kept its old trip name, so
# "S-101" (vehicle 1, run 01) sat on the 9th lane (production plan RP-2026-06-1754678,
# trip_group MIX-d859747188e5, VHL-L-0015).
#
# A trip name is the lane's row on the board plus a two-digit sequence. The save now
# renames a run into the series of the lane it is on - see
# RoutePlan._rename_into_series - and this clears what earlier saves already wrote.
#
# The repair is the same code the save runs, so the patch and the live rule cannot
# disagree. Draft and Active plans are repaired; Expired ones are history and are left.
#
# Rows are written with db.set_value (update_modified=False) rather than by saving the
# Route Plan: saving would re-run capacity validation, and a patch must not fail
# because some unrelated lane on a months-old plan no longer passes.
#
# The manifests of today and later follow the plan, because the driver reads the name
# there; past manifests are a record of what was driven and are left alone. Rerunning
# changes nothing: once a run is in its series it is never renamed again.


def execute():
	if not frappe.db.exists("DocType", "Route Plan Assignment"):
		return

	today = getdate(nowdate())
	runs = {}  # (plan, vehicle, trip_group, old name) -> new name

	for plan in frappe.get_all(
		"Route Plan", filters={"status": ["in", ["Draft", "Active"]]}, pluck="name"
	):
		doc = frappe.get_doc("Route Plan", plan)
		before = {row.name: row.trip_name for row in doc.assignments}

		doc._rename_duplicate_trip_names()

		for row in doc.assignments:
			old = before.get(row.name)
			if old == row.trip_name:
				continue
			frappe.db.set_value(
				"Route Plan Assignment", row.name, "trip_name", row.trip_name,
				update_modified=False,
			)
			runs[(plan, row.vehicle, row.trip_group, old)] = row.trip_name

	manifest_rows = _rename_manifest_rows(runs, today)

	if runs:
		# No commit here: the patch runner commits, and committing inside would break
		# the transaction a test wraps this in.
		for (plan, vehicle, _group, old), new in sorted(
			runs.items(), key=lambda item: (item[0][0], str(item[0][1]), str(item[0][3]))
		):
			print(f"Trip rename: {plan} {vehicle}: {old} -> {new}")
		vehicles = {(plan, vehicle) for (plan, vehicle, _g, _o) in runs}
		print(
			f"Trip rename: renamed {len(runs)} run(s) on {len(vehicles)} vehicle(s); "
			f"{manifest_rows} manifest row(s) from {today} on followed"
		)


def _rename_manifest_rows(runs, today) -> int:
	"""Follow the renamed runs on the manifests dated today or later."""
	if not runs or not frappe.db.exists("DocType", "Transportation Manifest Details"):
		return 0

	has_vehicle = frappe.get_meta("Transportation Manifest").has_field("vehicle")
	parents = {}
	updated = 0

	for (_plan, vehicle, group, old), new in runs.items():
		if not group:
			continue
		for detail in frappe.get_all(
			"Transportation Manifest Details",
			filters={"trip_id": group, "trip_name": old, "parenttype": "Transportation Manifest"},
			fields=["name", "parent"],
		):
			if detail.parent not in parents:
				parents[detail.parent] = frappe.db.get_value(
					"Transportation Manifest", detail.parent,
					["schedule_date"] + (["vehicle"] if has_vehicle else []), as_dict=True,
				)
			manifest = parents[detail.parent]
			if not manifest or not manifest.schedule_date or getdate(manifest.schedule_date) < today:
				continue
			if has_vehicle and manifest.vehicle and vehicle and manifest.vehicle != vehicle:
				continue
			frappe.db.set_value(
				"Transportation Manifest Details", detail.name, "trip_name", new,
				update_modified=False,
			)
			updated += 1

	return updated
