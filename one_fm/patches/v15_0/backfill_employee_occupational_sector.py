"""WI-002745: fill in the occupational sector on the employees that already hold a PAM designation.

``custom_occupational_sector`` is fetched from the designation, and a fetch only runs when
the form is saved. A new field therefore arrives empty on every existing record and stays
empty until somebody opens that employee - which across thousands of records is nobody.

Updated in place rather than through the document: the value is a copy of what the
designation already says, every Employee controller hook would fire for a figure none of
them read, and a save of every employee on the site is not what a backfill should cost.
"""

import frappe
from frappe.query_builder import DocType, functions as fn

FIELDNAME = "custom_occupational_sector"
SOURCE = "occupational_sector"


def execute():
	if not frappe.db.has_column("Employee", FIELDNAME):
		# The column arrives with the patch that adds the field. If it is not here yet
		# there is nothing to fill in, and the next run will do it.
		return

	Employee = DocType("Employee")

	# Grouped by sector, not by designation. There are three thousand designations and
	# nine sectors between them, and the column carries no index - one statement per
	# designation would scan the employee table three thousand times over.
	designations_by_sector = {}
	for designation in frappe.get_all(
		"PAM Designation List",
		filters={SOURCE: ["is", "set"]},
		fields=["name", SOURCE],
		limit_page_length=0,
	):
		designations_by_sector.setdefault(designation[SOURCE], []).append(designation.name)

	for sector, designations in designations_by_sector.items():
		(
			frappe.qb.update(Employee)
			.set(Employee[FIELDNAME], sector)
			.where(Employee.one_fm_pam_designation.isin(designations))
			.where(fn.IfNull(Employee[FIELDNAME], "") != sector)
		).run()

	# An employee who holds no designation, or one that names no sector, has nothing to
	# copy - and a value left behind by an earlier designation would read as fact. Cleared
	# rather than left, so the column says what the designation says or says nothing.
	named = [name for names in designations_by_sector.values() for name in names]
	(
		frappe.qb.update(Employee)
		.set(Employee[FIELDNAME], None)
		.where(fn.IfNull(Employee[FIELDNAME], "") != "")
		.where(fn.IfNull(Employee.one_fm_pam_designation, "").notin(named or [""]))
	).run()
