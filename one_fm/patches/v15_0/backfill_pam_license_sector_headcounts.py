"""Fill in the actual headcounts on every PAM licence sector row (WI-002091).

The two figures - Actual Number of Nationals and Actual Number of Expats - are derived
from the employees on the licence rather than typed, and have been since WI-002091. But
nothing has ever filled them in for the employees who were already on the books: the
handler that maintains them runs when an Employee is saved, and an employee nobody has
touched since has never been counted. On this site all twelve sector rows carry ratios an
operator typed and no headcounts at all.

There is a backfill already - set_pam_license_stats_status_read_only, WI-002135 - and it
counted nothing. It is dated 2026-08-20; repoint_pam_file_links_to_license_details
(WI-002233) is dated 2026-08-29. Until that one ran, the licence number an Employee
carries and the number a licence is found by were two different numbers, so no licence
matched anybody. The patch is marked done and will not run again, which is why this exists
rather than a re-dating of that one.

THE PART THAT WAS ACTUALLY MISSING
----------------------------------
A recount today would still have counted nothing, and would have written a confident zero
onto every row. The chain from an employee to a sector is

    Employee.one_fm_pam_designation -> PAM Designation List.occupational_sector

and `occupational_sector` is empty on all 2,786 designation records. The sector each one
belongs to is on the same record under a different name: مهنة_قرار_النسبة, a Select that is
filled in on every single one, whose five values are exactly five of the six Occupational
Sector records. The Link was added afterwards and never populated from it.

So this runs in two halves: give every designation the sector it already states, then
recount. Without the first half the second is arithmetic over an empty join.
"""

import frappe
from frappe.query_builder import DocType, Field

from one_fm.grd.doctype.pam_license_details.pam_license_details import recount_sector

# The Select that has held the sector all along. Named here rather than read from the meta
# because the whole point is that it is not the field anything else reads.
RATIO_DECISION_FIELD = "مهنة_قرار_النسبة"

# The two figures this patch exists to fill. A row already carrying one is a row somebody
# has a number on, and is not overwritten with a zero that means "nothing to count".
HEADCOUNT_FIELDS = ("national_number_of_workers", "expatriate_number_of_workers")


def execute():
	frappe.reload_doc("grd", "doctype", "pam_designation_list")
	frappe.reload_doc("grd", "doctype", "pam_license_stats")
	frappe.reload_doc("grd", "doctype", "pam_license_details")

	filled = fill_designation_sectors()
	counted, skipped = recount_every_sector_row()

	frappe.log(
		f"WI-002091 backfill: {filled} designation(s) given an occupational sector, "
		f"{counted} sector row(s) recounted, {skipped} left alone."
	)


def fill_designation_sectors() -> int:
	"""Give every PAM designation the occupational sector it already names.

	Only where the Link is empty, so a sector somebody has corrected by hand is left
	as they set it, and only where the Select's value is the name of a real Occupational
	Sector - a value that matches nothing would otherwise write a broken Link, and the
	count that reads it would fail rather than be wrong.

	One statement rather than 2,786 writes. `modified` is deliberately not touched: this
	restates what the record already said, and 2,786 rows changing timestamp would read as
	somebody having edited the master data today.
	"""
	sectors = frappe.get_all("Occupational Sector", pluck="name")
	if not sectors:
		return 0

	Designation = DocType("PAM Designation List")
	# Built with Field rather than as an attribute: the column name is Arabic, and
	# Designation.field(...) resolves to a column called "field" on the table.
	stated = Field(RATIO_DECISION_FIELD, table=Designation)

	to_fill = (
		frappe.qb.from_(Designation)
		.select(frappe.qb.terms.Function("Count", Designation.name))
		.where(Designation.occupational_sector.isnull() | (Designation.occupational_sector == ""))
		.where(stated.isin(sectors))
	).run()[0][0]

	if not to_fill:
		return 0

	(
		frappe.qb.update(Designation)
		.set(Designation.occupational_sector, stated)
		.where(Designation.occupational_sector.isnull() | (Designation.occupational_sector == ""))
		.where(stated.isin(sectors))
	).run()

	return to_fill


def mapped_sectors() -> set:
	"""The sectors at least one designation belongs to.

	A sector nothing maps to can only ever count zero people, whatever the licence holds -
	so a zero written against one says "no designation points here", not "nobody works
	here", and the two are not the same statement to put in front of PAM.
	"""
	return set(
		frappe.get_all(
			"PAM Designation List",
			filters={"occupational_sector": ["is", "set"]},
			pluck="occupational_sector",
			distinct=True,
		)
	)


def recount_every_sector_row():
	"""Recount each sector row on each licence, through the same code an Employee save uses.

	recount_sector rather than arithmetic repeated here: it is what the handler calls, so
	the backfill cannot compute a figure the live path would not, and it writes the derived
	columns - required nationals, excess, allowed, violated and the status - along with the
	two headcounts, which otherwise would be left describing yesterday's numbers.

	Only rows that already exist. A licence can have employees in a sector it has no row
	for, and recount_sector would add one; that is a change to what the licence declares
	rather than a figure being filled in, and it is not what this patch was asked for.
	"""
	mapped = mapped_sectors()
	counted = skipped = 0

	for name in frappe.get_all("PAM License Details", pluck="name"):
		license = frappe.get_doc("PAM License Details", name)
		number = license.civil_id_number_for_licensing
		if not number:
			# Every licence with a blank number would otherwise match every other one.
			skipped += len(license.pam_license_stats)
			continue

		for row in license.pam_license_stats:
			if not row.occupational_sector:
				skipped += 1
				continue

			if row.occupational_sector not in mapped and any(row.get(f) for f in HEADCOUNT_FIELDS):
				# Nothing maps to this sector, so the recount is a guaranteed zero - and
				# there is already a figure on the row. Replacing it would be this patch
				# erasing a number rather than filling one in.
				skipped += 1
				continue

			recount_sector(number, row.occupational_sector)
			counted += 1

	return counted, skipped
