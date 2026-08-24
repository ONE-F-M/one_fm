# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""Rename the report "Operations Monthly Attendance Sheet" -> "Monthly Payroll Attendance Sheet".

WI-002153 AC1. Renamed rather than left to the report sync to create afresh, so the Print
Format that prints the sheet follows instead of pointing at a report nobody maintains.

**Must run pre-model-sync.** The report sync runs between the two patch passes; if it went
first the rename would refuse a name that already exists.

The 175 Prepared Reports are deliberately not repointed - their ``report_name`` is a Data
field, and each was computed under the old rules, so serving one under the new name would
hand a payroll operator stale figures.
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
	# the doc - so the field it is named after has to follow, or the next save reverts it.
	frappe.db.set_value("Report", NEW, "report_name", NEW, update_modified=False)

	frappe.db.commit()
