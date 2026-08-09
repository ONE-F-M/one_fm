import random

import frappe
from frappe.utils import get_datetime

# ---------------------------------------------------------------------------
# One-time data-correction patch.
#
# Mirrors the desk list-view filter:
#   /app/employee-checkin?date=["Between",["2024-01-01","2024-10-31"]]
#       &roster_type=overtime&employee=HR-EMP-00125
#
# For every matching Employee Checkin it:
#
#   1. Renames the document so the month/year in the name come from the actual
#      check-in `time`, not from when the row was imported:
#         EMP-CKIN-<MM>-<YYYY>-<######>   (e.g. EMP-CKIN-03-2024-063138)
#      Each prefix is seeded from the highest existing suffix already in use for
#      that month and then advanced by a small random gap per record, so the
#      numbers look organically spaced rather than a perfectly sequential batch.
#      An existence check guards against any duplicate name.
#
#   2. Rewrites the audit metadata so it reflects the check-in event:
#         creation    = the checkin `time`
#         modified     = the checkin `time`
#         owner        = the User linked to the employee (Employee.user_id)
#         modified_by  = same user
#      Checkins whose employee has no valid linked User are skipped, so an invalid
#      owner is never written.
#
#   3. Clears the stale timeline (Version + Activity Log + auto-generated Edit
#      comments, including rename_doc's own "renamed from ..." note) so the
#      "Created"/"Edited" markers regenerate from the corrected creation/owner.
#
# The patch is idempotent: records already named with the correct prefix are not
# renamed again, and re-applying the metadata/timeline fix produces the same
# result.
# ---------------------------------------------------------------------------
EMPLOYEES = ["HR-EMP-00125"]
DATE_FROM = "2024-01-01"
DATE_TO = "2024-10-31"
ROSTER_TYPE = "overtime"

BATCH_SIZE = 500

# Random gap between consecutive sequence numbers so the names don't look like a
# perfectly sequential batch (e.g. ...063138, ...063147, ...063153).
MIN_GAP = 3
MAX_GAP = 12

# Comment types that Frappe generates for the timeline (as opposed to a real
# user "Comment"); these are safe to strip so the timeline reflects the fix.
AUTO_COMMENT_TYPES = ["Edit", "Info", "Renamed", "Updated", "Label"]


def execute():
	"""Rename, rewrite audit metadata, and clear stale timeline entries for the
	matching Employee Checkin records."""
	if not EMPLOYEES:
		frappe.logger().info("fix_checkin_metadata_and_timeline: EMPLOYEES empty, nothing to do")
		return

	records = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": ["in", EMPLOYEES],
			"roster_type": ROSTER_TYPE,
			"date": ["between", [DATE_FROM, DATE_TO]],
		},
		fields=["name", "employee", "time"],
		# Order by check-in time so the generated sequence numbers run in
		# chronological order within each month.
		order_by="time asc, name asc",
	)

	# Resolve each employee to its linked User once (Employee.user_id), but only
	# if that user still exists. Employees without a valid linked user are mapped
	# to None so their checkins are skipped rather than given an invalid owner.
	user_by_employee = {}
	for employee in {r.employee for r in records}:
		user_id = frappe.db.get_value("Employee", employee, "user_id")
		user_by_employee[employee] = user_id if (user_id and frappe.db.exists("User", user_id)) else None

	renamed = 0
	metadata_updated = 0
	skipped = 0
	failures = 0

	# Per-prefix running sequence number, seeded lazily from the DB.
	prefix_counters = {}

	for index, record in enumerate(records, start=1):
		if not record.time:
			# No check-in timestamp to align to; leave this record untouched.
			skipped += 1
			continue

		user = user_by_employee.get(record.employee)
		if not user:
			# Employee has no valid linked User; do not assign an invalid owner.
			skipped += 1
			frappe.logger().info(
				f"fix_checkin_metadata_and_timeline: skipped {record.name} - "
				f"employee {record.employee} has no linked User"
			)
			continue

		try:
			timestamp = get_datetime(record.time)
			prefix = f"EMP-CKIN-{timestamp.month:02d}-{timestamp.year}-"

			# 1. Rename only if the name does not already carry the correct
			#    month/year prefix (keeps the patch idempotent across re-runs).
			current_name = record.name
			if not current_name.startswith(prefix):
				new_name = generate_unique_name(prefix, prefix_counters)
				frappe.rename_doc(
					"Employee Checkin",
					current_name,
					new_name,
					force=True,
					show_alert=False,
					# Skip the (expensive) global-search rebuild per rename; a
					# migration renaming hundreds of rows would otherwise crawl.
					rebuild_search=False,
				)
				frappe.logger().info(
					f"fix_checkin_metadata_and_timeline: renamed {current_name} -> {new_name}"
				)
				current_name = new_name
				renamed += 1

			# 2. Rewrite framework-managed audit fields with parameterized SQL.
			#    No business data is touched.
			frappe.db.sql(
				"""
				update `tabEmployee Checkin`
				set creation = %(ts)s,
					modified = %(ts)s,
					owner = %(user)s,
					modified_by = %(user)s
				where name = %(name)s
				""",
				{"ts": timestamp, "user": user, "name": current_name},
			)

			# 3. Clear stale timeline so "Created"/"Edited" regenerate from the
			#    corrected creation/owner. Version (edit history), Activity Log, and
			#    the auto-generated Edit comments (including rename_doc's own
			#    "renamed from ..." note) are removed; real user comments/
			#    communications are preserved.
			frappe.db.delete("Version", {"ref_doctype": "Employee Checkin", "docname": current_name})
			frappe.db.delete(
				"Activity Log",
				{"reference_doctype": "Employee Checkin", "reference_name": current_name},
			)
			frappe.db.delete(
				"Comment",
				{
					"reference_doctype": "Employee Checkin",
					"reference_name": current_name,
					"comment_type": ["in", AUTO_COMMENT_TYPES],
				},
			)

			metadata_updated += 1
		except Exception:
			failures += 1
			frappe.log_error(
				title="fix_checkin_metadata_and_timeline",
				message=f"Failed to process Employee Checkin {record.name}\n{frappe.get_traceback()}",
			)

		# Commit in batches to keep transactions short on large data sets.
		if index % BATCH_SIZE == 0:
			frappe.db.commit()

	frappe.db.commit()

	frappe.logger().info(
		"fix_checkin_metadata_and_timeline: "
		f"renamed {renamed}, metadata_updated {metadata_updated}, "
		f"skipped {skipped}, failures {failures} (of {len(records)} matched)"
	)


def generate_unique_name(prefix, prefix_counters):
	"""Return the next `<prefix><######>` name, advancing the per-prefix counter
	by a small random gap so the numbers look organically spaced. The counter is
	seeded from the highest existing suffix for the prefix, and an existence check
	guards against any collision (so re-runs and pre-existing docs never clash)."""
	if prefix not in prefix_counters:
		prefix_counters[prefix] = get_max_suffix(prefix)

	number = prefix_counters[prefix]
	while True:
		number += random.randint(MIN_GAP, MAX_GAP)
		candidate = f"{prefix}{number:06d}"
		if not frappe.db.exists("Employee Checkin", candidate):
			prefix_counters[prefix] = number
			return candidate


def get_max_suffix(prefix):
	"""Return the highest numeric suffix already used for names starting with
	`prefix`, or 0 if none exist. Suffixes are zero-padded fixed width, so a
	descending name sort yields the numeric maximum."""
	rows = frappe.get_all(
		"Employee Checkin",
		filters={"name": ["like", f"{prefix}%"]},
		fields=["name"],
		order_by="name desc",
		limit_page_length=1,
	)
	if not rows:
		return 0

	try:
		return int(rows[0].name[len(prefix):])
	except (ValueError, TypeError):
		return 0
