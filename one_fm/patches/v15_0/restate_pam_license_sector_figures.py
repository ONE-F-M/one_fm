"""Restate every PAM licence sector row after the two corrections (WI-002094, WI-002091).

Reported from production the morning after the headcounts were first filled in:

  * Excess Nationals was subtracting the wrong way round. WI-002094 writes it as required
    minus actual, which is a shortfall - so the field showed 0 on every sector that had
    surplus nationals and a number only where the licence was short. Now actual minus
    required, confirmed with the process owner.
  * The headcount counted only Active employees, leaving 90 people off these two licences
    who are still employed under them - on vacation, not returned from leave, on a court
    case or absconding. Now everybody but those who have left.

Both figures are written onto the child rows with db_set and are not recomputed until
something touches the licence or an employee on it, so the rows on the site still hold
what the old rules produced. This restates them.

Nothing here decides anything: it calls the same recount an Employee save calls, through
the traversal the first backfill already used, so the corrections are applied by the code
that now holds them rather than repeated here.
"""

import frappe

from one_fm.patches.v15_0.backfill_pam_license_sector_headcounts import recount_every_sector_row


def execute():
	frappe.reload_doc("grd", "doctype", "pam_license_stats")
	frappe.reload_doc("grd", "doctype", "pam_license_details")

	counted, skipped = recount_every_sector_row()

	frappe.log(
		f"WI-002094/WI-002091 restatement: {counted} sector row(s) recounted, {skipped} left alone."
	)
