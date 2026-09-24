"""Restate every PAM licence sector row after the headcount rule changed.

The count now takes the employees under the company's residency rather than everybody
who has not left. On the live data that is the only rule that reproduces the figures PAM
gave for ONE FM Private.

The figures are written onto the child rows with db_set and are not recomputed until
something touches the licence or an employee on it, so they are restated here through the
same recount an Employee save calls.
"""

import frappe

from one_fm.patches.v15_0.backfill_pam_license_sector_headcounts import recount_every_sector_row


def execute():
	frappe.reload_doc("grd", "doctype", "pam_license_stats")
	frappe.reload_doc("grd", "doctype", "pam_license_details")

	counted, skipped = recount_every_sector_row()

	frappe.log(f"PAM recount: {counted} sector row(s) restated, {skipped} left alone.")
