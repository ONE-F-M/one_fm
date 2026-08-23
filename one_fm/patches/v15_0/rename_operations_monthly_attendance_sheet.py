# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""Rename the report "Operations Monthly Attendance Sheet" -> "Monthly Payroll Attendance Sheet".

WI-002153 AC1. The sheet no longer covers only Operations: the shift_working gate came
off the employee query in the same work item, so non-shift staff, subcontractors and
service providers appear on it too. The old name said otherwise.

Renamed rather than left to the report sync to create afresh, because the name is the
docname: the Print Format that prints the sheet links to it by name, and a second Report
doc beside the old one would leave the old one live, visible and unmaintained.

The 175 Prepared Reports already generated are deliberately *not* repointed. Their
``report_name`` is a Data field, not a Link, so the rename leaves them alone - and that is
what we want: every one of them was computed under the old rules (an "Other" column, a
shift-working-only employee set, Day Off OT narrowing instead of consolidating), so
serving one under the new name would hand a payroll operator stale figures. Unmatched,
the report simply regenerates, and Frappe's own expiry clears them.

**This must run pre-model-sync.** The report sync runs between the pre and post patch
passes; if it went first it would create "Monthly Payroll Attendance Sheet" from the JSON
and the rename would then refuse a name that already exists, leaving the old doc behind
with everything still pointing at it.

No-op on a site that never had the old name - a fresh install creates the report from the
JSON already renamed.
"""

import frappe

OLD = "Operations Monthly Attendance Sheet"
NEW = "Monthly Payroll Attendance Sheet"


def execute():
	if not frappe.db.exists("Report", OLD):
		return

	if frappe.db.exists("Report", NEW):
		frappe.log_error(
			title=f"rename_operations_monthly_attendance_sheet: {OLD} and {NEW} both exist",
			message=(
				f"Cannot rename {OLD!r} to {NEW!r} because {NEW!r} already exists. This happens "
				"when the report sync ran before this patch. Repoint the Print Format still "
				f"linked to {OLD!r}, delete it, then re-run."
			),
		)
		return

	# force, because Report is not a renameable doctype by default (allow_rename = 0).
	frappe.rename_doc("Report", OLD, NEW, force=True, show_alert=False)

	# Report is named field:report_name, and rename_doc moves the docname without saving
	# the doc - so the field it is named after has to follow by hand, or the next save
	# renames it straight back.
	frappe.db.set_value("Report", NEW, "report_name", NEW, update_modified=False)

	frappe.db.commit()
