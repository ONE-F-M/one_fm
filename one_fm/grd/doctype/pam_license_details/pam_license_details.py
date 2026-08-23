# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""A single PAM license and the sector statistics PAM rations it by (WI-002102).

The two actual headcounts on each sector row are derived from the employees on the license
rather than typed (WI-002091): PAM counts nationals and expatriates per occupational
sector, and an operator maintaining those numbers by hand is one transfer away from a
licence that reads compliant when it is not.
"""

import frappe
from frappe.model.document import Document
from frappe.query_builder import DocType

KUWAITI = "Kuwaiti"

# The Employee fields a headcount depends on. A save that touches none of them cannot have
# moved anybody between licences or sectors, and Employee is saved constantly - so the
# recount is skipped rather than run on every save.
#
# The occupational sector is not an Employee field: it is fetched from the employee's PAM
# designation, so a change of designation is what moves them between sectors.
WATCHED_EMPLOYEE_FIELDS = (
	"pam_file",
	"pam_file_number",
	"one_fm_pam_designation",
	"one_fm_nationality",
	"status",
)


class PAMLicenseDetails(Document):
	pass


def update_counts_from_employee(doc, method=None):
	"""Recount whatever this employee just joined or left (WI-002091).

	Both sides, because a designation or a licence number that changed moves the employee
	out of one sector row and into another - recounting only where they are now would leave
	the row they came from carrying them for good.

	A recount rather than an increment: the count is a query over the employees on the
	licence, so it cannot drift out of step with them the way a running total would.
	"""
	if not any(doc.has_value_changed(fieldname) for fieldname in WATCHED_EMPLOYEE_FIELDS):
		return

	before = doc.get_doc_before_save()
	for license_number, sector in {
		_license_and_sector(doc),
		_license_and_sector(before) if before else None,
	} - {None}:
		recount_sector(license_number, sector)


def _license_and_sector(employee):
	"""The licence number and occupational sector this employee counts against, or None."""
	license_number = employee.get("pam_file_number")
	designation = employee.get("one_fm_pam_designation")
	if not license_number or not designation:
		return None

	sector = frappe.db.get_value("PAM Designation List", designation, "occupational_sector")
	if not sector:
		return None

	return license_number, sector


def recount_sector(license_number, sector):
	"""Write the national and expatriate headcounts onto every row for this licence/sector.

	Keyed on the licence *number* rather than the licence record: that is what an Employee
	carries, and PAM's own numbering, so a licence renamed here still counts the same
	people.

	Written with db_set on the child row rather than by saving the parent, so a headcount
	moving does not drag a licence through validation - and does not need permission to
	edit a licence, which the employee's own editor has no reason to hold.
	"""
	rows = frappe.get_all(
		"PAM License Stats",
		filters={"occupational_sector": sector, "parenttype": "PAM License Details"},
		fields=["name", "parent"],
	)
	if not rows:
		return

	licenses = set(
		frappe.get_all(
			"PAM License Details",
			filters={"civil_id_number_for_licensing": license_number},
			pluck="name",
		)
	)
	rows = [row for row in rows if row.parent in licenses]
	if not rows:
		return

	nationals, expatriates = count_workers(license_number, sector)
	for row in rows:
		frappe.db.set_value(
			"PAM License Stats",
			row.name,
			{
				"national_number_of_workers": str(nationals),
				"expatriate_number_of_workers": str(expatriates),
			},
			update_modified=False,
		)


def count_workers(license_number, sector):
	"""How many nationals and expatriates this licence holds in this sector.

	Only active employees: someone who has left is not on the licence, and PAM counts who
	is working under it today.

	One query, grouped on nationality, rather than one count per side - the join to
	PAM Designation List is the expensive half and there is no reason to pay for it twice.
	"""
	Employee = DocType("Employee")
	Designation = DocType("PAM Designation List")

	rows = (
		frappe.qb.from_(Employee)
		.join(Designation)
		.on(Employee.one_fm_pam_designation == Designation.name)
		.select(Employee.one_fm_nationality, frappe.qb.terms.Function("Count", Employee.name).as_("count"))
		.where(Employee.pam_file_number == license_number)
		.where(Employee.status == "Active")
		.where(Designation.occupational_sector == sector)
		.groupby(Employee.one_fm_nationality)
	).run(as_dict=True)

	nationals = sum(row["count"] for row in rows if row["one_fm_nationality"] == KUWAITI)
	expatriates = sum(row["count"] for row in rows if row["one_fm_nationality"] != KUWAITI)

	return nationals, expatriates


def recount_license(license_name):
	"""Recount every sector row on one licence.

	Used to fill in a licence that has just been configured, and by the migration backfill -
	the per-employee hook only fires when an employee is saved.
	"""
	license = frappe.get_doc("PAM License Details", license_name)
	for row in license.pam_license_stats:
		if row.occupational_sector:
			recount_sector(license.civil_id_number_for_licensing, row.occupational_sector)
