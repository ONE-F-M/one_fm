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
from frappe.utils import flt

KUWAITI = "Kuwaiti"

# WI-002099: on top of the ratio, PAM allows each occupational sector a fixed number of
# expatriates over what the ratio alone would permit. The allowance is per sector and is
# government-set, so it is a table rather than a setting.
#
# Keyed on the Occupational Sector record names, which are the Arabic sector names PAM
# uses. WI-002099's own text writes the exempt sector as "مهن غير مشمولة / معفي"; the record
# is "مهن غير مشمولة بالنسبة", and the record name is what the data holds.
SECTOR_EXPAT_ALLOWANCE = {
	"علميون و فنيون": 5,
	"مديرون": 1,
	"كتبة و تنفيذيون": 2,
	"مقدمي خدمات": 10,
	"بائعون": 3,
}

# The sector PAM exempts from the ratio entirely: no expatriates are allowed against it,
# whatever the licence's nationals and ratio say.
EXEMPT_SECTOR = "مهن غير مشمولة بالنسبة"

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
	def validate(self):
		self.set_sector_figures()

	def set_sector_figures(self):
		"""Derive every figure a sector row computes from its ratio (WI-002094).

		On validate as well as on a recount, because the ratio is the half an operator
		types: it is entered here and the figures that follow from it have to move with it
		without waiting for somebody to be transferred.
		"""
		for row in self.pam_license_stats:
			for fieldname, value in derived_figures(
				row.occupational_sector,
				row.ratio_number_of_national_workers,
				row.national_number_of_workers,
				row.expatriate_number_of_workers,
			).items():
				row.set(fieldname, value)


def round_to_half(value):
	"""PAM states its figures to the nearest half a person (WI-002094)."""
	return round(flt(value) * 2) / 2


def as_figure(value):
	"""A figure as it goes into a Data field: "3" rather than "3.0", "2.5" as it is."""
	value = round_to_half(value)
	return str(int(value)) if value == int(value) else str(value)


def expats_allowed(sector, ratio, nationals):
	"""How many expatriates PAM permits this sector (WI-002099).

	The nationals the licence actually holds carry a number of expatriates set by the
	ratio - nationals x (100 - ratio) / ratio - plus a fixed allowance PAM grants each
	sector on top.

	The exempt sector is allowed none: PAM does not ration it by the ratio at all, so there
	is no headcount to permit against.

	A ratio of zero or blank permits nothing: the formula divides by it, and a row nobody
	has configured yet should not read as an unlimited allowance.

	A sector with no entry in the table gets the ratio's own number and no allowance. That
	is a gap in the master data rather than a licence to invent a figure for it, and it is
	visible on the row as a number the operator can question.
	"""
	if sector == EXEMPT_SECTOR:
		return 0.0

	ratio = flt(ratio)
	if ratio <= 0:
		return 0.0

	return flt(nationals) * (100 - ratio) / ratio + SECTOR_EXPAT_ALLOWANCE.get(sector, 0)


def derived_figures(sector, ratio, nationals, expatriates):
	"""What one sector row's ratio and two actual headcounts imply.

	The ratio is the share of the workforce PAM requires to be Kuwaiti, so the nationals a
	licence needs to carry its expatriates is expatriates x ratio / (100 - ratio)
	(WI-002094).


	Outside 0 < ratio < 100 there is no requirement to state: at 100 the formula divides by
	zero, above it the answer is negative, and at 0 or blank PAM asks for no nationals in
	that sector. All three come out as no requirement rather than as an error - the ratio is
	typed by hand and a licence should not refuse to save because one row is unfilled.

	Excess Nationals is what the licence is still short of that requirement, and never less
	than zero: a sector already carrying enough nationals is not short of any.

	Number of Expats Violated is how far the sector is over its allowance (WI-002099) -
	actual expatriates minus the number allowed, never below zero. WI-002099 writes that
	subtraction the other way round, which would call a sector well under its allowance the
	most violated of all and a sector over the limit compliant; the direction here is the
	one that makes the figure and the Compliant / Non-Compliant status mean what they say.
	Reversing it is one line if PAM's own wording turns out to be literal.

	Kept as a plain function so the arithmetic can be checked without a licence, and so the
	controller and the recount both go through one copy of it.
	"""
	ratio = flt(ratio)

	required = 0.0
	if 0 < ratio < 100:
		required = flt(expatriates) * ratio / (100 - ratio)
	required = round_to_half(required)

	excess = max(required - flt(nationals), 0)

	allowed = round_to_half(expats_allowed(sector, ratio, nationals))
	violated = max(flt(expatriates) - allowed, 0)

	return {
		"required_number_of_national_workers": as_figure(required),
		"exceeding_the_ratio_number_of_national_workers": as_figure(excess),
		"exempt_number_of_workers": as_figure(allowed),
		"violation_number_of_workers": as_figure(violated)
	}


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
		figures = {
			"national_number_of_workers": str(nationals),
			"expatriate_number_of_workers": str(expatriates),
		}
		# The derived figures move with the counts they are derived from. Written here as
		# well as on validate because db_set bypasses the controller, and a row left with
		# yesterday's requirement beside today's headcount is worse than either.
		figures.update(
			derived_figures(
				sector,
				frappe.db.get_value("PAM License Stats", row.name, "ratio_number_of_national_workers"),
				nationals,
				expatriates,
			)
		)
		frappe.db.set_value("PAM License Stats", row.name, figures, update_modified=False)


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
