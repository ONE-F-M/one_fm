import frappe

# WI-002401: two runs on one vehicle answering to the same trip name.
#
# A trip name is how a run is identified on the timeline block, in the "Add Stop to which
# trip?" picker and on the driver's manifest, so a lane holding two runs called S-106 is
# ambiguous everywhere the name is all the reader has - vehicle 60/59220 had one at
# 05:30-06:05 and another at 22:00-23:15, both S-106.
#
# The canvas used to mint a name by COUNTING the runs on the lane, which re-issued a name
# the moment any run but the last was removed (fixed in WI-002160 by scanning for the next
# free sequence). It now also cannot happen at all, because the rule is enforced on the
# Route Plan itself - see RoutePlan._rename_duplicate_trip_names. This clears what the old
# behaviour already wrote.
#
# The repair is the same code the save runs, so the patch and the live rule can never
# disagree about what a correct lane looks like: the earliest run keeps the name and each
# later claimant takes the next free sequence in that lane's own series.
#
# Rows are written with db.set_value rather than by saving the Route Plan: saving would
# re-run the whole plan's capacity validation, and a patch must not fail because some
# unrelated lane on a months-old plan no longer passes.


def execute():
	if not frappe.db.exists("DocType", "Route Plan Assignment"):
		return

	renamed = 0
	for plan in frappe.get_all("Route Plan", pluck="name"):
		doc = frappe.get_doc("Route Plan", plan)
		before = {row.name: row.trip_name for row in doc.assignments}

		doc._rename_duplicate_trip_names()

		for row in doc.assignments:
			if before.get(row.name) == row.trip_name:
				continue
			frappe.db.set_value(
				"Route Plan Assignment", row.name, "trip_name", row.trip_name,
				update_modified=False,
			)
			renamed += 1

	if renamed:
		# No commit here: the patch runner commits, and committing inside would break
		# the transaction a test wraps this in.
		print(f"WI-002401: renamed {renamed} assignment row(s) off a duplicated trip name")
