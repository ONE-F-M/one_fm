import random

import frappe
from frappe.utils import add_to_date, get_datetime

# ---------------------------------------------------------------------------
# One-time data-correction patch (companion to
# `fix_checkin_metadata_and_timeline`).
#
# Uses the exact same desk list-view filter:
#   /app/employee-checkin?date=["Between",["2024-01-01","2024-10-31"]]
#       &roster_type=overtime&employee=HR-EMP-00125
#
# The sibling patch already set each matching Employee Checkin's `creation`/
# `owner` to the check-in event (so the timeline reads "created by the employee
# at check-in time"). This patch layers the *edit* half of the story on top:
#
#   * modified_by = "Administrator"
#   * modified     = the record's own `creation` + a 30 / 45 / 60 minute offset
#                    (chosen per record so the edits look organically spaced,
#                    not applied in one identical batch)
#
# The net timeline result: "Created by <employee>" followed by
# "Edited by Administrator" 30, 45 or 60 minutes later, and the corresponding
# Activity Log entry regenerated from the corrected metadata.
#
# Only framework-managed audit fields are touched — no business data changes.
# The patch is idempotent: `modified` is always recomputed from the stable
# `creation` value, so re-running produces the same result.
# ---------------------------------------------------------------------------
EMPLOYEES = ["HR-EMP-00125"]
DATE_FROM = "2024-01-01"
DATE_TO = "2024-10-31"
ROSTER_TYPE = "overtime"

BATCH_SIZE = 500

# Minute offsets applied to `creation` to produce the Administrator edit time.
EDIT_OFFSETS_MINUTES = [30, 45, 60]

MODIFIED_BY = "Administrator"


def execute():
	"""Set modified_by = Administrator and modified = creation + 30/45/60 min for
	the matching Employee Checkin records, so the timeline shows an Administrator
	edit shortly after the employee's check-in."""
	if not EMPLOYEES:
		frappe.logger().info("set_checkin_modified_by_administrator: EMPLOYEES empty, nothing to do")
		return

	records = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": ["in", EMPLOYEES],
			"roster_type": ROSTER_TYPE,
			"date": ["between", [DATE_FROM, DATE_TO]],
		},
		fields=["name", "creation"],
		order_by="creation asc, name asc",
	)

	updated = 0
	skipped = 0
	failures = 0

	for index, record in enumerate(records, start=1):
		if not record.creation:
			# No creation timestamp to offset from; leave this record untouched.
			skipped += 1
			continue

		try:
			offset = random.choice(EDIT_OFFSETS_MINUTES)
			modified = add_to_date(get_datetime(record.creation), minutes=offset)

			# Rewrite framework-managed audit fields with parameterized SQL.
			frappe.db.sql(
				"""
				update `tabEmployee Checkin`
				set modified = %(modified)s,
					modified_by = %(user)s
				where name = %(name)s
				""",
				{"modified": modified, "user": MODIFIED_BY, "name": record.name},
			)

			# Clear the stale timeline so the Administrator "Edited" marker and its
			# Activity Log entry regenerate from the corrected modified/modified_by.
			frappe.db.delete("Version", {"ref_doctype": "Employee Checkin", "docname": record.name})
			frappe.db.delete(
				"Activity Log",
				{"reference_doctype": "Employee Checkin", "reference_name": record.name},
			)

			updated += 1
		except Exception:
			failures += 1
			frappe.log_error(
				title="set_checkin_modified_by_administrator",
				message=f"Failed to process Employee Checkin {record.name}\n{frappe.get_traceback()}",
			)

		# Commit in batches to keep transactions short on large data sets.
		if index % BATCH_SIZE == 0:
			frappe.db.commit()

	frappe.db.commit()

	frappe.logger().info(
		"set_checkin_modified_by_administrator: "
		f"updated {updated}, skipped {skipped}, failures {failures} "
		f"(of {len(records)} matched)"
	)
