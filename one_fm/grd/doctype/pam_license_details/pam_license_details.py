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

# Every field the count reads. Employee is saved constantly; a save touching none of these
# cannot have moved anybody, so the recount is skipped.
# The sector comes from the PAM designation, so a change of designation moves the employee.
WATCHED_EMPLOYEE_FIELDS = (
	"pam_file",
	"pam_file_number",
	"one_fm_pam_designation",
	"one_fm_nationality",
	"under_company_residency",
)


class PAMLicenseDetails(Document):
	def validate(self):
		self.set_sector_figures()
		self.set_total_number_of_employees()
		self.set_quota_registrations()
		self.set_quota_visas_issued()

	def set_quota_visas_issued(self):
		"""Derive each quota row's issued-visa count (WI-002771).

		On validate for the same reason the registrations are: a row re-pointed at another
		quota type here should show its figure straight away.
		"""
		issued = visas_issued_by_quota(self.name, self.civil_id_number_for_licensing)
		for row in self.quota_classification:
			row.number_of_visas_issued = str(issued.get(row.type_of_quota, 0))

	def set_quota_registrations(self):
		"""Derive each quota row's registered headcount (WI-002769).

		On validate as well as on a recount, because a row added or re-pointed at another
		quota type here should show its figure without waiting for somebody to be
		transferred.
		"""
		for row in self.quota_classification:
			row.registered_numbers_of_employees = str(
				count_quota_employees(self.civil_id_number_for_licensing, row.type_of_quota)
			)

	def set_total_number_of_employees(self):
		"""How many people this licence carries, all sectors together (WI-002768).

		Derived here as well as on the per-employee recount, so a licence opened and saved
		shows the figure even if nobody has been transferred since the last recount.
		"""
		self.total_number_of_employees = str(
			count_license_employees(self.civil_id_number_for_licensing)
		)

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

	Excess Nationals is how many nationals the licence carries over that requirement, and
	never less than zero: a sector short of the requirement is not in excess of it.

	WI-002094 writes that subtraction the other way round - required minus actual - which
	is a shortfall, not an excess, and read literally it made the field useless: it showed
	0 on every sector that genuinely had surplus nationals and a number only on the ones
	that were short. The clamp is what gives it away. "If negative, display 0" only makes
	sense in this direction; in the other it hides exactly the thing the field is named
	after. Reported from production against real counts, and the process owner confirmed
	the direction - the same call already made on the violation line below.

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

	excess = max(flt(nationals) - required, 0)

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

	An insert is always a recount, and is asked before has_value_changed rather than left to
	it. On this Employee, has_value_changed answers False for every field on an insert:
	one_fm's after_insert reloads the document, and after_insert runs before on_update, so by
	the time this handler is reached the before-state is the row that was just written and
	every field equals itself. A new employee was silently never counted.
	"""
	if not doc.flags.in_insert and not any(
		doc.has_value_changed(fieldname) for fieldname in WATCHED_EMPLOYEE_FIELDS
	):
		return

	# Same reason: on an insert the before-state is this employee, not who they used to be.
	before = None if doc.flags.in_insert else doc.get_doc_before_save()
	for license_number, sector in {
		_license_and_sector(doc),
		_license_and_sector(before) if before else None,
	} - {None}:
		recount_sector(license_number, sector)

	# WI-002768: the licence's own headcount, which is not a sector figure. Recounted from
	# the licence NUMBER alone, because an employee with no PAM designation still counts
	# against the licence - _license_and_sector gives up on them, and the total must not.
	for license_number in {doc.get("pam_file_number"), before.get("pam_file_number") if before else None} - {None, ""}:
		recount_license_total(license_number)
		# WI-002769: the quota rows are a second grouping of the same employees, by the
		# quota type their designation belongs to rather than by its sector.
		recount_quota_rows(license_number)


def update_counts_from_designation(doc, method=None):
	"""Recount when a designation is moved to a different occupational sector or quota.

	The sector is not on the employee - it is on the designation they hold - so moving a
	designation moves everybody holding it, and no Employee is saved when that happens.
	Without this the licence keeps yesterday's figures until somebody edits an employee.

	Both sectors, on every licence holding one of those employees: the sector they left
	has to give them up as well as the one they joined.
	"""
	if doc.is_new():
		return

	sector_moved = doc.has_value_changed("occupational_sector")
	# WI-002769: the quota type is on the designation too, and moving one moves everybody
	# holding it out of one quota row and into another.
	quota_moved = doc.has_value_changed("quota_type")
	if not sector_moved and not quota_moved:
		return

	before = doc.get_doc_before_save()
	numbers = {
		number
		for number in frappe.get_all(
			"Employee", filters={"one_fm_pam_designation": doc.name}, pluck="pam_file_number"
		)
		if number
	}
	if not numbers:
		return

	sectors = {doc.occupational_sector, before.occupational_sector if before else None} - {None, ""}

	for number in numbers:
		if sector_moved:
			for sector in sectors:
				recount_sector(number, sector)
		if quota_moved:
			# Every row on the licence, not just the two quotas named: the whole table is
			# a handful of rows, and recounting it is cheaper than reasoning about which
			# licences carry which of the two.
			recount_quota_rows(number)


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

	Counts employees under the company's residency. That is what the licence is: somebody
	off it is not on the licence, whatever their employment status says.

	The sector is not a field on Employee - it is reached through the employee's PAM
	designation, which is what the join below is for.

	One query grouped on nationality; the join to PAM Designation List is the expensive
	half and there is no reason to pay for it twice.
	"""
	Employee = DocType("Employee")
	Designation = DocType("PAM Designation List")

	rows = (
		frappe.qb.from_(Employee)
		.join(Designation)
		.on(Employee.one_fm_pam_designation == Designation.name)
		.select(Employee.one_fm_nationality, frappe.qb.terms.Function("Count", Employee.name).as_("count"))
		.where(Employee.pam_file_number == license_number)
		.where(Employee.under_company_residency == 1)
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


def count_license_employees(license_number) -> int:
	"""How many people this licence carries (WI-002768).

	Under the company's residency, which is what the licence IS: somebody off it is not on
	the licence, whatever their employment status says. The same rule the sector headcounts
	use (WI-002091), so the total and the figures beneath it cannot disagree about who is
	on the licence.

	No join to the designation. The sector counts need it to know which row an employee
	belongs to; this is every employee on the licence, including the ones whose designation
	has not been set yet - and leaving those out would make the total quietly smaller than
	the sum of what PAM counts.
	"""
	if not license_number:
		return 0

	return frappe.db.count(
		"Employee", {"pam_file_number": license_number, "under_company_residency": 1}
	)


def recount_license_total(license_number):
	"""Write the licence headcount onto every licence carrying this number.

	db_set rather than a save, for the same reason the sector figures are: a headcount
	moving must not drag a licence through validation, and must not need permission to
	edit a licence that the employee's own editor has no reason to hold.
	"""
	licenses = frappe.get_all(
		"PAM License Details",
		filters={"civil_id_number_for_licensing": license_number},
		pluck="name",
	)
	if not licenses:
		return

	total = str(count_license_employees(license_number))
	for license_name in licenses:
		frappe.db.set_value(
			"PAM License Details",
			license_name,
			"total_number_of_employees",
			total,
			update_modified=False,
		)


def count_quota_employees(license_number, quota_type) -> int:
	"""How many of this licence's employees hold a designation in this quota (WI-002769).

	Three conditions, all of them the story's: the licence, the company's residency, and
	the quota type - which is not on the employee but on the PAM designation they hold, so
	the join is what makes the count possible at all.

	A row with no quota type yet counts nobody. Falling back to "everyone on the licence"
	would put the whole workforce in whichever row an operator had not finished
	configuring, and it would look like a real figure.
	"""
	if not license_number or not quota_type:
		return 0

	Employee = DocType("Employee")
	Designation = DocType("PAM Designation List")

	rows = (
		frappe.qb.from_(Employee)
		.join(Designation)
		.on(Employee.one_fm_pam_designation == Designation.name)
		.select(frappe.qb.terms.Function("Count", Employee.name).as_("count"))
		.where(Employee.pam_file_number == license_number)
		.where(Employee.under_company_residency == 1)
		.where(Designation.quota_type == quota_type)
	).run(as_dict=True)

	return rows[0]["count"] if rows else 0


def recount_quota_rows(license_number):
	"""Write the registered headcount onto every quota row of every licence with this number.

	The whole table rather than one row: it is a handful of rows, and recounting it is
	cheaper than working out which one an employee moved between - their designation can
	have changed quota as easily as their licence can have changed.

	Unlike the sector rows, a missing row is NOT added. A quota row exists because PAM
	allocated this licence a quota of that type; inventing one from the employees who
	happen to hold such a designation would state an allocation nobody granted.
	"""
	licenses = frappe.get_all(
		"PAM License Details",
		filters={"civil_id_number_for_licensing": license_number},
		pluck="name",
	)
	if not licenses:
		return

	counts = {}
	for license_name in licenses:
		# WI-002771: the issued visas are per LICENCE rather than per licence number,
		# because a Visa Request names the licence record it was raised against.
		issued = visas_issued_by_quota(license_name, license_number)

		rows = frappe.get_all(
			"Quota Classification",
			filters={
				"parent": license_name,
				"parenttype": "PAM License Details",
				"parentfield": "quota_classification",
			},
			fields=["name", "type_of_quota"],
		)
		for row in rows:
			quota_type = row["type_of_quota"]
			if quota_type not in counts:
				counts[quota_type] = str(count_quota_employees(license_number, quota_type))

			frappe.db.set_value(
				"Quota Classification",
				row["name"],
				{
					"registered_numbers_of_employees": counts[quota_type],
					"number_of_visas_issued": str(issued.get(quota_type, 0)),
				},
				update_modified=False,
			)


# WI-002771: the state a Visa Request reaches when PAM and MOI have both said yes and the
# visa exists. Only those count against a quota - anything earlier is an application, not
# a visa.
VISA_COMPLETED = "Completed"


def visas_issued_by_quota(license_name, license_number) -> dict:
	"""Visas issued against this licence, counted per quota type (WI-002771).

	Keyed on the Visa Request's own PAM File and PAM Designation rather than on an
	employee: at this point there is no employee. The visa has been issued and the person
	has not arrived, which is the whole reason the figure is separate from the registered
	headcount beside it.

	A cancelled visa is not an issued one. WI-002744 already works out which completed
	requests have had their visa given back, and the same answer is used here - the story's
	last criterion is that a completed cancellation takes the visa back out of this count
	and returns it to the available quota.

	Returns {quota type: count}; a quota with no visas simply does not appear.
	"""
	from one_fm.visa_management.doctype.visa_request.visa_request import (
		cancelled_visa_requests,
	)

	licenses = [name for name in {license_name} if name]
	if license_number:
		licenses += frappe.get_all(
			"PAM License Details",
			filters={"civil_id_number_for_licensing": license_number},
			pluck="name",
		)
	licenses = list(dict.fromkeys(licenses))
	if not licenses:
		return {}

	requests = frappe.get_all(
		"Visa Request",
		filters=[
			["custom_pam_file", "in", licenses],
			["workflow_state", "=", VISA_COMPLETED],
			["custom_pam_designation_list", "is", "set"],
		],
		fields=["name", "custom_pam_designation_list"],
	)
	if not requests:
		return {}

	released = cancelled_visa_requests([request["name"] for request in requests])

	designations = {
		request["custom_pam_designation_list"]
		for request in requests
		if request["name"] not in released
	}
	if not designations:
		return {}

	quota_of = dict(
		frappe.get_all(
			"PAM Designation List",
			filters={"name": ["in", list(designations)]},
			fields=["name", "quota_type"],
			as_list=True,
		)
	)

	counts = {}
	for request in requests:
		if request["name"] in released:
			continue
		quota_type = quota_of.get(request["custom_pam_designation_list"])
		if not quota_type:
			# A designation nobody has put in a quota yet. Counted against no row rather
			# than against the first one - a visa in the wrong quota reads as headroom
			# that is not there.
			continue
		counts[quota_type] = counts.get(quota_type, 0) + 1

	return counts


def update_quota_from_visa_request(doc, method=None):
	"""Recount a licence's quota rows when a visa request reaches or leaves Completed.

	Without this the issued figure only moved when somebody saved an Employee - and the
	whole point of the figure is the gap before an employee exists.

	Both licences, because a request re-pointed at another PAM File takes its visa with it.
	"""
	before = None if doc.flags.in_insert else doc.get_doc_before_save()

	if not doc.flags.in_insert and not any(
		doc.has_value_changed(fieldname)
		for fieldname in ("workflow_state", "custom_pam_file", "custom_pam_designation_list")
	):
		return

	for license_name in {
		doc.get("custom_pam_file"),
		before.get("custom_pam_file") if before else None,
	} - {None, ""}:
		recount_license_quota(license_name)


def update_quota_from_visa_cancellation(doc, method=None):
	"""Recount when a cancellation is completed: the visa goes back to the quota.

	The Visa Request it names is the way back to the licence - a cancellation carries no
	PAM File of its own.
	"""
	if not doc.get("visa_request_id"):
		return

	license_name = frappe.db.get_value("Visa Request", doc.visa_request_id, "custom_pam_file")
	if license_name:
		recount_license_quota(license_name)


def recount_license_quota(license_name):
	"""Rewrite one licence's quota rows from the employees and visas it carries."""
	number = frappe.db.get_value(
		"PAM License Details", license_name, "civil_id_number_for_licensing"
	)
	if not number:
		return

	recount_quota_rows(number)
