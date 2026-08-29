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

# WI-002135: the two things a sector row's Status can say, and the only thing that decides
# between them - whether the sector is over its expatriate allowance at all.
COMPLIANT = "Compliant"
NON_COMPLIANT = "Non-Compliant"

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


def to_whole(value):
	"""A figure as PAM states it: a whole number of people (WI-002094, WI-002099).

	Half rounds up rather than to even, and by hand rather than through round() - every
	figure here is a headcount and cannot be negative, and a licence that reads compliant on
	one site and not on another because of a rounding setting is worse than either answer.
	"""
	return int(flt(value) + 0.5)


def as_figure(value):
	"""A figure as it goes into a Data field: "3" rather than "3.0"."""
	return str(to_whole(value))


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

	The exempt sector is the exception WI-002099 spells out: "there will be no expat
	violation, as Kuwaitis are not allowed for this role... if the number of expats is 100,
	the violation will be 0". PAM does not ration it, so it is allowed none and is over by
	none - the allowance of zero is a statement that the ratio does not apply to it, not a
	limit every expatriate on the books breaks.

	The Status follows from the violation and nothing else (WI-002135): over the allowance by
	any amount is Non-Compliant, otherwise Compliant. Derived here rather than left as a
	Select the operator picks, so it cannot contradict the figure printed beside it.

	Kept as a plain function so the arithmetic can be checked without a licence, and so the
	controller and the recount both go through one copy of it.
	"""
	ratio = flt(ratio)

	required = 0.0
	if 0 < ratio < 100:
		required = flt(expatriates) * ratio / (100 - ratio)
	required = to_whole(required)

	excess = max(required - flt(nationals), 0)

	allowed = to_whole(expats_allowed(sector, ratio, nationals))
	violated = 0.0 if sector == EXEMPT_SECTOR else max(flt(expatriates) - allowed, 0)

	return {
		"required_number_of_national_workers": as_figure(required),
		"exceeding_the_ratio_number_of_national_workers": as_figure(excess),
		"exempt_number_of_workers": as_figure(allowed),
		"violation_number_of_workers": as_figure(violated),
		"status": NON_COMPLIANT if violated > 0 else COMPLIANT,
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

	A licence that has never carried anybody in this sector has no row for it, and the sector
	an employee belongs to is decided by their PAM designation rather than by what somebody
	remembered to configure. So the row is added rather than the recount quietly doing nothing
	(WI-002091, second criterion) - an employee counted against no row is an employee PAM
	counts and the licence does not.

	Only where there is somebody to count. The recount also runs for the sector an employee
	has just left, and adding an empty row there would grow the table by one every time
	anybody changed designation.

	Written with db_set on the child row rather than by saving the parent, so a headcount
	moving does not drag a licence through validation - and does not need permission to
	edit a licence, which the employee's own editor has no reason to hold.
	"""
	licenses = frappe.get_all(
		"PAM License Details",
		filters={"civil_id_number_for_licensing": license_number},
		pluck="name",
	)
	if not licenses:
		return

	nationals, expatriates = count_workers(license_number, sector)

	for license_name in licenses:
		row = frappe.db.get_value(
			"PAM License Stats",
			{
				"parent": license_name,
				"parenttype": "PAM License Details",
				"parentfield": "pam_license_stats",
				"occupational_sector": sector,
			},
			["name", "ratio_number_of_national_workers"],
			as_dict=True,
		)
		if not row:
			if not (nationals or expatriates):
				continue
			row = add_sector_row(license_name, sector)

		figures = {
			"national_number_of_workers": str(nationals),
			"expatriate_number_of_workers": str(expatriates),
		}
		# The derived figures move with the counts they are derived from. Written here as
		# well as on validate because db_set bypasses the controller, and a row left with
		# yesterday's requirement beside today's headcount is worse than either.
		figures.update(
			derived_figures(sector, row.ratio_number_of_national_workers, nationals, expatriates)
		)
		frappe.db.set_value("PAM License Stats", row.name, figures, update_modified=False)


def add_sector_row(license_name, sector):
	"""Give a licence the sector row it has no configuration for yet.

	Inserted as a child in its own right rather than by saving the licence, for the same
	reason the headcounts are written with db_set.

	The ratio is left blank. It is the one figure on the row PAM sets and an operator types,
	and inventing one would state a requirement nobody has been given - so until it is filled
	in the row allows no expatriates and reads Non-Compliant if it holds any, which is the
	same thing an unconfigured row typed by hand has always said.
	"""
	row = frappe.get_doc({
		"doctype": "PAM License Stats",
		"parenttype": "PAM License Details",
		"parentfield": "pam_license_stats",
		"parent": license_name,
		"occupational_sector": sector,
		"idx": frappe.db.count(
			"PAM License Stats", {"parent": license_name, "parentfield": "pam_license_stats"}
		) + 1,
	})
	row.insert(ignore_permissions=True)
	return row


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
