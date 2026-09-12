"""WI-002316: the ERF Reason for Request option "UnPlanned" is gone.

The business analyst replaced it with "Other" and "Client ERF Hire". Records still
carrying the retired word are not left behind: a Select value that is no longer an
option fails Frappe's own validation on the next save, and a workflow action saves the
document - so an Accepted or Submit to Recruitment Manager ERF would become
unactionable rather than merely odd-looking.

They move to "Other", which is what the option list now offers for a reason it does not
name, and the retired word is written into Reason for (Other) so nothing is lost.
Written straight to the rows: these are submitted and cancelled documents, and
re-saving one from a patch would fight that.
"""

import frappe

RETIRED = "UnPlanned"
REPLACEMENT = "Other"


def execute():
	rows = frappe.get_all("ERF", filters={"reason_for_request": RETIRED}, pluck="name")
	for name in rows:
		existing = frappe.db.get_value("ERF", name, "reason_for_other")
		frappe.db.set_value(
			"ERF",
			name,
			{
				"reason_for_request": REPLACEMENT,
				# Only when the analyst has not already written something there.
				"reason_for_other": existing or RETIRED,
			},
			update_modified=False,
		)

	left_behind = frappe.db.count("ERF", {"reason_for_request": RETIRED})
	if left_behind:
		frappe.throw(f"{left_behind} ERF rows still carry {RETIRED!r}")

	print(f"WI-002316: moved {len(rows)} ERF rows from {RETIRED!r} to {REPLACEMENT!r}")
