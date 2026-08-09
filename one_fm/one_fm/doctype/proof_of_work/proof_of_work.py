# Copyright (c) 2026, ONEFM and contributors
# For license information, please see license.txt

import io
import re
import zipfile

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import (
	add_days,
	cint,
	cstr,
	date_diff,
	escape_html,
	flt,
	formatdate,
	get_first_day,
	get_last_day,
	getdate,
)

from one_fm.one_fm import google_credentials

# Canonical values stored in the "Generation Basis" Select field.
GENERATION_BASIS_OPTIONS = ("Shift Hours", "Attendance Day", "Both")

# Basis stamped on bulk-generated records (WI-001808). The generator no longer asks
# for one - the Contract Item Rate Type decides per Sale Item - but the field still
# backs the two paths Rate Type does not cover (an approved Attendance Amendment, and
# a Contract Item with no Rate Type set), where "Both" reports days OR hours to match
# the Letter's existing OR layout.
DEFAULT_GENERATION_BASIS = "Both"

# Attendance status -> single-letter cell in the monthly grid (used by the
# reusable get_pow_attendance_report data layer).
ATTENDANCE_ABBR = {
	"Present": "P",
	"Working": "P",
	"Work From Home": "WFH",
	"Absent": "A",
	"On Leave": "L",
	"Half Day": "HD",
	"Day Off": "DO",
	"Client Day Off": "CDO",
	"Holiday": "H",
	"On Hold": "OH",
	"Fingerprint Appointment": "FA",
	"Medical Appointment": "MA",
	"Client Interview": "CI",
}

# Attendance Amendment workflow state that marks it as "approved". The workflow
# keeps docstatus at 0 even for this state, so approval is a workflow_state check.
APPROVED_AMENDMENT_STATE = "Approved"

# Full month names, indexed 1..12 to match the Attendance Amendment "month" field.
MONTH_NAMES = (
	"",
	"January",
	"February",
	"March",
	"April",
	"May",
	"June",
	"July",
	"August",
	"September",
	"October",
	"November",
	"December",
)

# Attendance statuses that count as a worked/present day.
PRESENT_STATUSES = {"Present", "Working", "Work From Home"}

# Cells that count towards the "Days Off" column on the Attendance Report.
DAY_OFF_ABBRS = {"DO", "CDO"}


def _attendance_abbr(status: str) -> str:
	"""Legend abbreviation for an attendance status, falling back to its initial."""
	return ATTENDANCE_ABBR.get(status) or (status or "")[:1].upper()


# Cells that represent a day actually worked, and so carry hours on an Hourly Sale
# Item. Derived from PRESENT_STATUSES so the two cannot drift apart; Half Day is worked
# too, and carries whatever hours were recorded against it.
WORKED_ABBRS = {_attendance_abbr(status) for status in PRESENT_STATUSES} | {"HD"}

# Standard month used for the contractual justification (Column 3). Fixed by
# business policy: a contracted head is expected to cover 30 days / 208 hours a
# month, independent of the per-item shift length.
STANDARD_MONTH_DAYS = 30
STANDARD_MONTH_HOURS = 208


class ProofofWork(Document):
	pass


def _guard_permission():
	"""Only users who can create a Proof of Work may use the generator."""
	if not frappe.has_permission("Proof of Work", "create"):
		frappe.throw(
			_("You do not have permission to generate Proof of Work records."),
			frappe.PermissionError,
		)


def _get_month_range(month: int, year: int):
	"""Return (first_day, last_day) date objects for the given month/year."""
	month = cint(month)
	year = cint(year)
	if month < 1 or month > 12:
		frappe.throw(_("Month must be between 1 and 12."))
	if year < 1900 or year > 3000:
		frappe.throw(_("Please provide a valid Year."))

	anchor = getdate(f"{year}-{month:02d}-01")
	return get_first_day(anchor), get_last_day(anchor)


# ---------------------------------------------------------------------------
# Source resolution & aggregation
#
# Data-sourcing hierarchy (per the user story):
#   1. An APPROVED "Attendance Amendment" for the contract/month is the source
#      of truth. Match is preferred on the amendment's `contract` field and
#      falls back to `project` (the contract field is read-only and frequently
#      left blank), always scoped to month + year + Approved state.
#   2. If no approved amendment exists, fall back to the standard "Attendance"
#      records for the project in the period.
#
# One Proof of Work Item row is produced per Sale Item. `contractual_hours`
# (Column 3) is the legal justification: contracted head-count (Contract Item
# `count`) x the standard month (30 days / 208 hours). `actual_hours` and
# `staff_breakdown` (Column 1, grouped by identical time worked) come from the
# resolved source above.
# ---------------------------------------------------------------------------


def resolve_attendance_source(contract: str, project: str, month: int, year: int):
	"""
	Resolve the source of attendance data for a POW period.

	Returns a tuple ``(source_type, reference)`` where ``source_type`` is either
	``"amendment"`` (with ``reference`` = the Attendance Amendment name) or
	``"attendance"`` (with ``reference`` = ``None``).
	"""
	month_name = MONTH_NAMES[cint(month)]
	year_str = cstr(cint(year))
	base_filters = {
		"workflow_state": APPROVED_AMENDMENT_STATE,
		"month": month_name,
		"year": year_str,
	}

	# Prefer matching on the amendment's own contract field ...
	if contract:
		match = frappe.get_all(
			"Attendance Amendment",
			filters={**base_filters, "contract": contract},
			pluck="name",
			order_by="modified desc",
			limit=1,
		)
		if match:
			return "amendment", match[0]

	# ... otherwise fall back to the project (contract is often blank).
	if project:
		match = frappe.get_all(
			"Attendance Amendment",
			filters={**base_filters, "project": project},
			pluck="name",
			order_by="modified desc",
			limit=1,
		)
		if match:
			return "amendment", match[0]

	return "attendance", None


_SHIFT_HOURS_RE = re.compile(r"(\d+)HR", re.IGNORECASE)


def _shift_hours_from_item(item_code: str) -> float:
	"""Hours-per-shift encoded in the sale item code, e.g. '...-30DY-12HR' -> 12.

	The Contract Item ``working_hours``/``working_days`` fields are unmaintained
	in production, so the shift length is read from the item code (the same
	value used to name the item).
	"""
	match = _SHIFT_HOURS_RE.search(item_code or "")
	return flt(match.group(1)) if match else 0.0


def _contracted_count_by_sale_item(contract_name: str) -> dict:
	"""
	Contracted head-count per Sale Item, from the Contract Item ``count`` field
	(Service items only). This is the "20 staff" the contract legally commits to,
	and the basis for the Column 3 justification.

	Returns ``{sale_item: contracted_count}``.
	"""
	result = {}
	for it in frappe.get_all(
		"Contract Item",
		filters={"parent": contract_name, "parenttype": "Contracts", "item_type": "Service"},
		fields=["item_code", "count"],
	):
		if it.item_code:
			result[it.item_code] = result.get(it.item_code, 0) + cint(it.count)
	return result


def _rate_type_by_sale_item(contract_name: str) -> dict:
	"""
	Contract Item Rate Type per Sale Item (WI-001700 update).

	Rate Type decides which metric a Sale Item is measured in - Daily and Monthly in
	present days, Hourly in shift hours. Where one Sale Item appears on several Contract
	Item rows, an Hourly row wins: the item is billed by the hour, so days would understate
	it.

	Returns ``{sale_item: rate_type}``.
	"""
	result = {}
	for it in frappe.get_all(
		"Contract Item",
		filters={"parent": contract_name, "parenttype": "Contracts", "item_type": "Service"},
		fields=["item_code", "rate_type"],
	):
		if not it.item_code:
			continue
		if it.rate_type == "Hourly" or it.item_code not in result:
			result[it.item_code] = it.rate_type or ""
	return result


def _non_manpower_amount_by_category(contract_name: str) -> list:
	"""
	Contracted amount per Contract Item Category for the non-manpower lines (WI-001808).

	The manpower tables cover Contract Items with Item Type "Service". "Items" rows are
	the non-manpower ones - annual maintenance, pest control, handyman and the like - and
	they carry no attendance, so there is nothing to count: they are reported as a
	contracted amount per category.

	``item_code`` is blank on most of these rows in production, so the category is the
	only stable grouping key. ``rate`` is the figure that is consistently filled, with
	``amount`` as the fallback where a row leaves it at zero.

	Returns ``[{"contract_item_category": str, "amount": float}, ...]`` ordered by
	category.
	"""
	if not contract_name:
		return []

	totals = {}
	for it in frappe.get_all(
		"Contract Item",
		filters={
			"parent": contract_name,
			"parenttype": "Contracts",
			"item_type": "Items",
		},
		fields=["contract_item_category", "rate", "amount"],
	):
		category = it.contract_item_category
		if not category:
			# Without a category the row cannot be placed in the rollup.
			continue
		totals[category] = totals.get(category, 0.0) + (flt(it.rate) or flt(it.amount))

	return [
		{"contract_item_category": category, "amount": totals[category]}
		for category in sorted(totals)
	]


def _populate_pow_non_manpower_items(doc):
	"""Fill the ``proof_of_work_items_nonmanpower`` rollup table on a POW document."""
	doc.set("proof_of_work_items_nonmanpower", [])
	for row in _non_manpower_amount_by_category(doc.contract):
		doc.append("proof_of_work_items_nonmanpower", row)


def _basis_for_rate_type(rate_type: str, source_type: str, generation_basis: str) -> str:
	"""
	The metric one Sale Item is reported in (WI-001700 update).

	Without an Attendance Amendment the Contract Item's Rate Type decides: Daily and
	Monthly are counted in present days, Hourly in shift hours. When the contract does have
	an amendment the figures are shown as generated, so the document's own generation basis
	stands - as does it for a Contract Item with no Rate Type set, which leaves existing
	behaviour untouched.
	"""
	if source_type == "amendment":
		return generation_basis

	if rate_type == "Hourly":
		return "Shift Hours"
	if rate_type in ("Daily", "Monthly"):
		return "Attendance Day"

	return generation_basis


def _uses_nominal_shift_hours(rate_type: str, source_type: str) -> bool:
	"""
	Whether hours come from the shift length rather than the clock (WI-001700 update).

	The update says an Hourly Sale Item "Fetch Shift Hours", which is the nominal length
	in the item code (``-12HR``) x days present - so the figures come out whole. Actual
	recorded working_hours are what produced values like 540.96, and they still drive the
	amendment path, where the data is shown as generated.
	"""
	return source_type != "amendment" and rate_type == "Hourly"


def _item_types_by_sale_item(sale_items) -> dict:
	"""
	Item Type per Sale Item, comma separated where an item carries more than one.

	The Attendance Report shows these beside the Sale Item Code instead of in a column
	(WI-001700 update), so several types have to collapse into one string.
	"""
	if not sale_items:
		return {}

	types = {}
	for row in frappe.get_all(
		"Item", filters={"name": ["in", list(sale_items)]}, fields=["name", "item_type"]
	):
		if not row.item_type:
			continue
		existing = types.setdefault(row.name, [])
		if row.item_type not in existing:
			existing.append(row.item_type)

	return {name: ", ".join(values) for name, values in types.items()}


def _blank_source_entry() -> dict:
	return {"hours": 0.0, "days": 0.0, "staff": {}}


def _source_from_amendment(amendment_name: str, total_days: int) -> dict:
	"""
	Aggregate actual effort per Sale Item from an approved Attendance Amendment.

	Returns ``{sale_item: {"hours": float, "days": float, "staff": {...}}}``.
	"""
	doc = frappe.get_doc("Attendance Amendment", amendment_name)
	agg = {}

	for row in doc.get("attendance_details"):
		sale_item = row.sale_item
		if not sale_item:
			# Rows without a resolvable Sale Item can't map to a POW item row.
			continue

		emp_hours = 0.0
		emp_days = 0.0
		for i in range(1, total_days + 1):
			status = row.get(f"day_{i}")
			hour_val = row.get(f"day_{i}_hour")

			hours = 0.0
			if hour_val not in (None, "", "N/A"):
				hours = flt(hour_val)

			if hours > 0:
				emp_hours += hours
				emp_days += 1
			elif status in PRESENT_STATUSES:
				emp_days += 1
			elif status == "Half Day":
				emp_days += 0.5

		entry = agg.setdefault(sale_item, _blank_source_entry())
		entry["hours"] += emp_hours
		entry["days"] += emp_days

		staff_key = row.employee or row.employee_id or row.employee_name
		entry["staff"][staff_key] = {
			"name": row.employee_name or "",
			"id": row.employee_id or row.employee or "",
			"hours": emp_hours,
			"days": emp_days,
		}

	return agg


def _source_from_attendance(project: str, first_day, last_day) -> dict:
	"""
	Aggregate actual effort per Sale Item from standard Attendance records.

	Sale Item is resolved via the attendance's Operations Role. Returns
	``{sale_item: {"hours": float, "days": float, "staff": {...}}}``.
	"""
	agg = {}
	if not project:
		return agg

	Attendance = frappe.qb.DocType("Attendance")
	OperationsRole = frappe.qb.DocType("Operations Role")

	records = (
		frappe.qb.from_(Attendance)
		.left_join(OperationsRole)
		.on(Attendance.operations_role == OperationsRole.name)
		.select(
			Attendance.employee,
			Attendance.employee_name,
			Attendance.status,
			Attendance.working_hours,
			OperationsRole.sale_item.as_("sale_item"),
		)
		.where(
			(Attendance.docstatus == 1)
			& (Attendance.project == project)
			& (Attendance.attendance_date >= first_day)
			& (Attendance.attendance_date <= last_day)
		)
	).run(as_dict=True)

	for r in records:
		sale_item = r.sale_item
		if not sale_item:
			continue

		hours = flt(r.working_hours)
		if r.status in PRESENT_STATUSES:
			day = 1.0
		elif r.status == "Half Day":
			day = 0.5
		else:
			day = 0.0

		entry = agg.setdefault(sale_item, _blank_source_entry())
		entry["hours"] += hours
		entry["days"] += day

		staff = entry["staff"].setdefault(
			r.employee,
			{"name": r.employee_name or "", "id": r.employee or "", "hours": 0.0, "days": 0.0},
		)
		staff["hours"] += hours
		staff["days"] += day

	return agg


def _actual_hours(
	source: dict, shift_hours: float, basis: str, nominal_shift_hours: bool = False
) -> float:
	"""Hours worked for a Sale Item.

	``nominal_shift_hours`` reports days x the shift length, which is what an Hourly Rate
	Type asks for. Otherwise recorded working hours are used, falling back to days x shift
	length when the source only carries statuses.
	"""
	if basis == "Attendance Day" or nominal_shift_hours:
		return flt(source.get("days", 0.0)) * shift_hours
	return flt(source.get("hours", 0.0)) or (flt(source.get("days", 0.0)) * shift_hours)


def _num(value) -> str:
	"""Render a number without a trailing ``.0`` but keep real decimals (e.g. 0.5)."""
	value = flt(value)
	if value == int(value):
		return str(int(value))
	return f"{value:.2f}".rstrip("0").rstrip(".")


def _group_breakdown(
	staff: dict, metric: str, shift_hours: float, nominal_shift_hours: bool = False
) -> str:
	"""
	Group distinct staff by identical time worked for one metric.

	``metric == "days"``  -> ``"- {n} Staff worked {v} days: {n*v} Days"``
	``metric == "hours"`` -> ``"- {n} Staff worked {v} Hours: {n*v} Hrs"``

	Every distinct individual is counted (relievers included), so the group
	totals sum to the actual worked total even when head-count exceeds the
	contracted count. Hours fall back to days x shift length when no numeric
	hours were recorded.
	"""
	groups = {}
	for info in staff.values():
		if metric == "days":
			value = flt(info.get("days", 0.0))
		elif nominal_shift_hours:
			# Shift length x days present, so an Hourly item reports whole hours.
			value = flt(info.get("days", 0.0)) * shift_hours
		else:
			value = flt(info.get("hours", 0.0)) or (flt(info.get("days", 0.0)) * shift_hours)
		key = round(value, 2)
		groups[key] = groups.get(key, 0) + 1

	lines = []
	for value in sorted(groups, reverse=True):
		n = groups[value]
		total = n * value
		if metric == "days":
			lines.append(f"- {n} Staff worked {_num(value)} days: {_num(total)} Days")
		else:
			lines.append(f"- {n} Staff worked {_num(value)} Hours: {_num(total)} Hrs")
	return "\n".join(lines)


def _fmt_staff_breakdown(
	source: dict, shift_hours: float, basis: str, nominal_shift_hours: bool = False
) -> str:
	"""Column 1: staff grouped by identical time worked. For "Both", the days
	breakdown, an "OR" line, then the hours breakdown."""
	staff = source.get("staff", {})
	if not staff:
		return _("No attendance recorded for this item in the period.")

	blocks = []
	if basis in ("Attendance Day", "Both"):
		blocks.append(_group_breakdown(staff, "days", shift_hours))
	if basis in ("Shift Hours", "Both"):
		blocks.append(_group_breakdown(staff, "hours", shift_hours, nominal_shift_hours))
	return "\nOR\n".join(b for b in blocks if b)


def _fmt_actual(
	source: dict, shift_hours: float, basis: str, nominal_shift_hours: bool = False
) -> str:
	"""Column 2: what was actually worked, in the metric the Rate Type asks for.

	The column is headed "Total number Days worked OR Total No of Hours worked", so a
	Daily or Monthly Sale Item belongs in days. It used to render hours unconditionally -
	and for those Rate Types the hours were days x the shift length, so a 344-day month
	printed as "4128.00 hrs" beside a contractual figure quoted in DAYS.

	Split on basis like the two columns either side of it, so all three of a row's
	figures are in the same unit.
	"""
	days = flt(source.get("days", 0.0))
	if nominal_shift_hours:
		hours = days * shift_hours
	else:
		hours = flt(source.get("hours", 0.0)) or (days * shift_hours)

	blocks = []
	if basis in ("Attendance Day", "Both"):
		blocks.append(f"{_num(days)} Days")
	if basis in ("Shift Hours", "Both"):
		blocks.append(f"{hours:.2f} hrs")
	return "\nOR\n".join(blocks)


def _fmt_contractual(count: int, basis: str) -> str:
	"""Column 3: contracted head-count x the standard month. For "Both", the days
	justification, an "OR" line, then the hours justification."""
	count = cint(count)
	blocks = []
	if basis in ("Attendance Day", "Both"):
		blocks.append(
			f"={{{count} staff * {STANDARD_MONTH_DAYS} days}} = {count * STANDARD_MONTH_DAYS} DAYS"
		)
	if basis in ("Shift Hours", "Both"):
		blocks.append(
			f"={{{count} staff * {STANDARD_MONTH_HOURS} hours}} = {count * STANDARD_MONTH_HOURS} HOURS"
		)
	return "\nOR\n".join(blocks)


def _populate_pow_items(doc, first_day, last_day):
	"""
	Fill the ``proof_of_work_item`` summary table on a POW document, one row per
	Sale Item, using the resolved data source. Called during generation only.

	contractual_hours = contracted head-count (Contract Item `count`) x the
	                    standard month (30 days / 208 hours), per generation basis.
	actual_hours      = hours worked from the resolved source.
	staff_breakdown   = distinct staff grouped by identical time worked.
	"""
	total_days = date_diff(last_day, first_day) + 1

	contracted = _contracted_count_by_sale_item(doc.contract)

	source_type, reference = resolve_attendance_source(
		doc.contract, doc.project, getdate(first_day).month, getdate(first_day).year
	)
	if source_type == "amendment":
		source = _source_from_amendment(reference, total_days)
	else:
		source = _source_from_attendance(doc.project, first_day, last_day)

	# Rate Type drives the metric per Sale Item; the document's basis is the fallback.
	rate_types = _rate_type_by_sale_item(doc.contract)
	# Only the Sale Items on the contract. A Proof of Work states work done against a
	# contract, so an item with attendance but no Contract Item line is not a row here.
	#
	# Note the consequence, which is deliberate: where the contract does not list the
	# service that was actually worked, that work is not reported at all. The Alghanim
	# Industries contract is such a case - its only Service line is a uniform - and its
	# summary is empty as a result. That is a contract to correct, not output to read.
	# The attendance sheet on the later pages still lists every employee who worked,
	# because it is built from attendance rather than from the contract.
	sale_items = sorted(contracted)

	# Resolve item_type for all sale items in one query, comma joined where an item
	# carries more than one.
	item_types = _item_types_by_sale_item(sale_items)

	doc.set("proof_of_work_item", [])
	for sale_item in sale_items:
		shift_hours = _shift_hours_from_item(sale_item)
		s_entry = source.get(sale_item, _blank_source_entry())
		rate_type = rate_types.get(sale_item, "")
		basis = _basis_for_rate_type(rate_type, source_type, doc.generation_basis)
		nominal = _uses_nominal_shift_hours(rate_type, source_type)

		doc.append(
			"proof_of_work_item",
			{
				"sale_item_code": sale_item,
				"item_type": item_types.get(sale_item, ""),
				"contractual_hours": _fmt_contractual(contracted.get(sale_item, 0), basis),
				"actual_hours": _fmt_actual(s_entry, shift_hours, basis, nominal),
				"staff_breakdown": _fmt_staff_breakdown(s_entry, shift_hours, basis, nominal),
			},
		)


@frappe.whitelist()
def get_eligible_contracts(month: int, year: int):
	"""
	Return active contracts that have logged attendance in the given month.

	A contract is eligible when:
	  1. Its workflow state is "Active", and
	  2. Its linked Project has at least one Attendance record in the month.

	Each row carries ``has_pow`` so the frontend can pre-tick only the
	contracts that do not already have a Proof of Work for this period.
	"""
	_guard_permission()

	first_day, last_day = _get_month_range(month, year)

	# Distinct projects that logged attendance in the selected month.
	# Server-side aggregation gated by the POW-create permission above,
	# so get_all (which skips user permissions) is appropriate here.
	attended_projects = frappe.get_all(
		"Attendance",
		filters={
			"attendance_date": ["between", [first_day, last_day]],
			"docstatus": ["<", 2],
			"project": ["is", "set"],
		},
		distinct=True,
		pluck="project",
	)

	if not attended_projects:
		return []

	contracts = frappe.get_all(
		"Contracts",
		filters={
			"workflow_state": "Active",
			"project": ["in", attended_projects],
		},
		fields=["name", "project", "client"],
		order_by="name asc",
	)

	if not contracts:
		return []

	# Contracts that already have a (non-cancelled) POW for this period.
	existing = set(
		frappe.get_all(
			"Proof of Work",
			filters={
				"contract": ["in", [c.name for c in contracts]],
				"start_date": first_day,
				"docstatus": ["<", 2],
			},
			pluck="contract",
		)
	)

	for c in contracts:
		c["has_pow"] = 1 if c.name in existing else 0

	return contracts


@frappe.whitelist(methods=["POST"])
def generate_proof_of_work(
	month: int, year: int, contracts, generation_basis: str = DEFAULT_GENERATION_BASIS
):
	"""
	Batch-create and submit one Proof of Work record per selected contract.

	Contracts that already have a POW for the period are skipped and reported back to
	the caller, as is any contract whose record fails to submit (WI-001808) - one bad
	contract must not hold up the rest of the month.

	``generation_basis`` is no longer collected by the generator dialog; it defaults to
	"Both" and stays on the document for the paths Rate Type does not cover.
	"""
	_guard_permission()

	if generation_basis not in GENERATION_BASIS_OPTIONS:
		frappe.throw(
			_("Invalid Generation Basis. Must be one of: {0}").format(
				", ".join(GENERATION_BASIS_OPTIONS)
			)
		)

	if isinstance(contracts, str):
		contracts = frappe.parse_json(contracts)

	if not contracts:
		frappe.throw(_("Please select at least one contract."))

	first_day, last_day = _get_month_range(month, year)

	created = []
	skipped = []

	for idx, contract_name in enumerate(contracts):
		if not frappe.db.exists("Contracts", contract_name):
			skipped.append({"contract": contract_name, "reason": _("Contract not found")})
			continue

		# Skip if a non-cancelled POW already exists for this contract + period.
		if frappe.db.exists(
			"Proof of Work",
			{
				"contract": contract_name,
				"start_date": first_day,
				"docstatus": ["<", 2],
			},
		):
			skipped.append(
				{"contract": contract_name, "reason": _("Proof of Work already exists")}
			)
			continue

		contract = frappe.db.get_value(
			"Contracts", contract_name, ["project", "client"], as_dict=True
		)

		doc = frappe.new_doc("Proof of Work")
		doc.contract = contract_name
		doc.project = contract.project
		doc.customer = contract.client
		doc.start_date = first_day
		doc.end_date = last_day
		doc.generation_basis = generation_basis

		# Fetch & lock the summary table from the strict source hierarchy
		# (approved Attendance Amendment first, else standard Attendance).
		_populate_pow_items(doc, first_day, last_day)
		# Non-manpower ("Items") contract lines, rolled up per category.
		_populate_pow_non_manpower_items(doc)

		doc.insert()

		# WI-001808: bulk generation submits. A record that will not submit is reported
		# and left as a draft to be fixed by hand, so the rest of the batch still goes
		# through. savepoint/rollback keeps a failed submit from poisoning the
		# transaction for the contracts that follow.
		savepoint = f"pow_submit_{idx}"
		frappe.db.savepoint(savepoint)
		try:
			doc.submit()
			created.append(doc.name)
		except Exception:
			frappe.db.rollback(save_point=savepoint)
			frappe.log_error(
				title="Proof of Work bulk submit failed", message=frappe.get_traceback()
			)
			skipped.append(
				{
					"contract": contract_name,
					"reason": _("Created as draft {0} - submit failed").format(doc.name),
				}
			)

	return {"created": created, "skipped": skipped}


# ---------------------------------------------------------------------------
# Attendance Report data (WI-001703): a monthly attendance grid grouped by
# Sale Item, from the resolved source. Consumed by the "Proof of Work
# Attendance Report" print format.
# ---------------------------------------------------------------------------


def _grid_from_amendment(amendment_name: str, total_days: int) -> dict:
	"""Per-employee day grid grouped by Sale Item, from an Attendance Amendment.

	Returns ``{sale_item: {emp_key: {employee_id, employee_name, days{}, total_present}}}``.
	"""
	doc = frappe.get_doc("Attendance Amendment", amendment_name)
	groups = {}
	for row in doc.get("attendance_details"):
		if not row.sale_item:
			continue
		emp_key = row.employee or row.employee_id or row.employee_name
		emp = groups.setdefault(row.sale_item, {}).setdefault(
			emp_key,
			{
				"employee_id": row.employee_id or row.employee or "",
				"employee_name": row.employee_name or "",
				"days": {},
				"total_present": 0.0,
			},
		)
		for i in range(1, total_days + 1):
			status = row.get(f"day_{i}")
			hour_val = row.get(f"day_{i}_hour")
			if hour_val not in (None, "", "N/A") and flt(hour_val) > 0:
				emp["days"][i] = "P"
				emp["total_present"] += 1.0
			elif status in PRESENT_STATUSES:
				emp["days"][i] = "P"
				emp["total_present"] += 1.0
			elif status == "Half Day":
				emp["days"][i] = "H"
				emp["total_present"] += 0.5
			elif status:
				emp["days"][i] = _attendance_abbr(status)
	return groups


def _grid_from_attendance(project: str, first_day, last_day) -> dict:
	"""Per-employee day grid grouped by Sale Item, from standard Attendance.

	Sale Item is resolved via the attendance's Operations Role.
	"""
	groups = {}
	if not project:
		return groups

	Attendance = frappe.qb.DocType("Attendance")
	OperationsRole = frappe.qb.DocType("Operations Role")
	records = (
		frappe.qb.from_(Attendance)
		.left_join(OperationsRole)
		.on(Attendance.operations_role == OperationsRole.name)
		.select(
			Attendance.employee,
			Attendance.employee_name,
			Attendance.status,
			Attendance.attendance_date,
			OperationsRole.sale_item.as_("sale_item"),
		)
		.where(
			(Attendance.docstatus == 1)
			& (Attendance.project == project)
			& (Attendance.attendance_date >= first_day)
			& (Attendance.attendance_date <= last_day)
		)
	).run(as_dict=True)

	for r in records:
		if not r.sale_item:
			continue
		emp = groups.setdefault(r.sale_item, {}).setdefault(
			r.employee,
			{
				"employee_id": r.employee or "",
				"employee_name": r.employee_name or "",
				"days": {},
				"total_present": 0.0,
			},
		)
		day = getdate(r.attendance_date).day
		if r.status in PRESENT_STATUSES:
			emp["days"][day] = _attendance_abbr(r.status)
			emp["total_present"] += 1.0
		elif r.status == "Half Day":
			emp["days"][day] = _attendance_abbr(r.status)
			emp["total_present"] += 0.5
		elif r.status:
			emp["days"][day] = _attendance_abbr(r.status)
	return groups


def _hour_cells(statuses: list, shift_hours: float) -> list:
	"""Day cells for a Sale Item reported in hours: the rostered shift length on a day
	worked, its status otherwise (WI-001808).

	The length rostered, not the hours clocked - that is what the summary counts an
	Hourly item in, since `_hours_for` multiplies days by the shift length for it, so
	the cells read in the same figure as page 1. A half day carries half a shift, which
	is how it is already counted towards the day total.

	A day that was not worked keeps its abbreviation: "0" against an absence reads as a
	figure rather than an explanation.
	"""
	cells = []

	for status in statuses:
		if status not in WORKED_ABBRS:
			cells.append(status)
			continue
		cells.append(_num(flt(shift_hours) * (0.5 if status == "HD" else 1.0)))

	return cells


@frappe.whitelist()
def get_pow_attendance_report(pow_name: str) -> dict:
	"""Structured monthly attendance grid for a POW, grouped by Sale Item.

	Drives the "Proof of Work Attendance Report" print format. Source is the
	approved Attendance Amendment when present, else standard Attendance.
	"""
	doc = frappe.get_doc("Proof of Work", pow_name)
	doc.check_permission("read")

	first_day = getdate(doc.start_date)
	last_day = getdate(doc.end_date)
	total_days = date_diff(last_day, first_day) + 1

	source_type, reference = resolve_attendance_source(
		doc.contract, doc.project, first_day.month, first_day.year
	)
	if source_type == "amendment":
		groups = _grid_from_amendment(reference, total_days)
	else:
		groups = _grid_from_attendance(doc.project, first_day, last_day)

	# The sheet reports against the contract, exactly as the summary does: a Sale Item
	# with attendance but no Contract Item line is not the contract's work and gets no
	# section here either. Without this the sheet contradicted page 1, listing staff
	# against an item the summary did not carry.
	contracted = _contracted_count_by_sale_item(doc.contract)
	groups = {item: grid for item, grid in groups.items() if item in contracted}

	item_types = _item_types_by_sale_item(list(groups))
	rate_types = _rate_type_by_sale_item(doc.contract)

	group_list = []
	for sale_item in sorted(groups):
		shift_hours = _shift_hours_from_item(sale_item)
		# The sheet reads in whatever the summary counts this Sale Item in, decided by
		# the one function page 1 uses - so the two pages cannot disagree. An Hourly
		# Rate Type lands on Shift Hours, and its day cells then carry hours worked
		# instead of the attendance status.
		basis = _basis_for_rate_type(
			rate_types.get(sale_item, ""), source_type, doc.generation_basis
		)
		by_hours = basis == "Shift Hours"
		rows = []
		staff = sorted(groups[sale_item].values(), key=lambda e: e["employee_name"] or "")
		for sn, emp in enumerate(staff, start=1):
			statuses = [emp["days"].get(i, "") for i in range(1, total_days + 1)]
			working_days = flt(emp["total_present"])
			days_off = sum(1 for cell in statuses if cell in DAY_OFF_ABBRS)

			cells = _hour_cells(statuses, shift_hours) if by_hours else statuses

			rows.append(
				{
					"sn": sn,
					"employee_id": emp["employee_id"],
					"employee_name": emp["employee_name"],
					"days": cells,
					"total_present": _num(working_days),
					"working_days": _num(working_days),
					"days_off": _num(days_off),
					"total_hours": _num(working_days * shift_hours),
				}
			)

		group_list.append(
			{
				"sale_item": sale_item,
				# WI-001700 update: the item type(s) are shown next to the Sale Item Code,
				# comma separated, and the Item Type column is dropped.
				"item_type": item_types.get(sale_item, ""),
				"employees": rows,
				"totals": {
					"employees": len(rows),
					"working_days": _num(sum(flt(r["working_days"]) for r in rows)),
					"days_off": _num(sum(flt(r["days_off"]) for r in rows)),
					"total_hours": _num(sum(flt(r["total_hours"]) for r in rows)),
				},
			}
		)

	# Weekday over d/m for each column, as the Attendance Amendment preview shows it.
	day_labels = []
	for offset in range(total_days):
		day = add_days(first_day, offset)
		day_labels.append(
			{
				"weekday": day.strftime("%a"),
				"date": f"{day.day}/{day.month}",
				"is_weekend": day.weekday() in (4, 5),
			}
		)

	return {
		"meta": {
			"contract": doc.contract,
			"project": doc.project,
			"customer": doc.customer,
			"month_name": MONTH_NAMES[first_day.month],
			"year": first_day.year,
			"total_days": total_days,
			"day_numbers": list(range(1, total_days + 1)),
			"day_labels": day_labels,
			"source_type": source_type,
		},
		"groups": group_list,
	}


# ---------------------------------------------------------------------------
# PDF export (WI-001703, reshaped by WI-001808): the POW Letter and the
# Attendance Report are concatenated into ONE PDF per contract - Letter first
# (the summary + signature page), Attendance Report after it (the per-employee
# detail grid). Bulk generation bundles one such PDF per contract into a ZIP.
# ---------------------------------------------------------------------------

# Print formats concatenated into the single per-contract PDF, in page order.
LETTER_PRINT_FORMAT = "Proof of Work Letter"
ATTENDANCE_PRINT_FORMAT = "Proof of Work Attendance Report"

# Characters that must not reach a filename inside a ZIP or a Content-Disposition
# header. Kept deliberately broad: contract names are free text and routinely carry
# dots, slashes and ampersands.
_UNSAFE_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]+')


def _build_zip(entries) -> bytes:
	"""Bundle ``[(filename, content_bytes), ...]`` into an in-memory ZIP.

	Pure/stdlib so it is testable without a Frappe context (see __main__).
	"""
	buf = io.BytesIO()
	with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
		for filename, content in entries:
			zf.writestr(filename, content)
	return buf.getvalue()


def _safe_filename(text: str) -> str:
	"""Collapse anything filesystem-hostile out of one filename component.

	Pure/stdlib so it is testable without a Frappe context (see __main__).
	"""
	cleaned = _UNSAFE_FILENAME_CHARS.sub(" ", cstr(text))
	# Collapse runs of whitespace so the " - " separators stay readable.
	return " ".join(cleaned.split())


def pdf_file_name(customer_name: str, contract: str, start_date) -> str:
	"""``<client name> - <contract name> - <MMM-YYYY>.pdf`` (WI-001808).

	Pure/stdlib apart from ``getdate`` so it is cheap to test.
	"""
	period = getdate(start_date).strftime("%b-%Y") if start_date else ""
	parts = [_safe_filename(p) for p in (customer_name, contract, period)]
	return " - ".join(p for p in parts if p) + ".pdf"


def _active_print_format(name: str):
	"""The named print format if it exists and is enabled, else ``None``.

	``None`` makes Frappe fall back to the default print view, so an export never
	hard-fails just because a format was disabled.
	"""
	return name if frappe.db.exists("Print Format", {"name": name, "disabled": 0}) else None


def _merged_pdf(doc) -> bytes:
	"""The POW Letter followed by the Attendance Report, as one PDF (WI-001808).

	Both formats embed the ONEFM logo themselves, so Frappe's automatic letter head is
	turned off to avoid a duplicate. The Letter is A4 portrait and the Attendance Report
	A4 landscape; pypdf keeps each page's own size, so the merged file is intentionally
	mixed-orientation.
	"""
	from pypdf import PdfWriter

	output = PdfWriter()
	for print_format in (LETTER_PRINT_FORMAT, ATTENDANCE_PRINT_FORMAT):
		frappe.get_print(
			"Proof of Work",
			doc.name,
			print_format=_active_print_format(print_format),
			as_pdf=True,
			output=output,
			no_letterhead=1,
		)

	with io.BytesIO() as merged:
		output.write(merged)
		return merged.getvalue()


def _pow_pdf_entry(doc) -> tuple:
	"""``(filename, pdf_bytes)`` for one POW, named per the AC."""
	customer_name = (
		frappe.db.get_value("Customer", doc.customer, "customer_name") if doc.customer else None
	) or doc.customer
	return pdf_file_name(customer_name, doc.contract, doc.start_date), _merged_pdf(doc)


@frappe.whitelist()
def export_pdf(name: str):
	"""Stream the single merged PDF (Letter + Attendance Report) for one POW.

	Read-only (renders PDFs, no mutation), so served over GET for a direct browser
	download.
	"""
	doc = frappe.get_doc("Proof of Work", name)
	doc.check_permission("read")

	filename, content = _pow_pdf_entry(doc)

	frappe.local.response.filename = filename
	frappe.local.response.filecontent = content
	frappe.local.response.type = "download"


# ---------------------------------------------------------------------------
# Google Drive delivery (WI-001981). The export uploads each merged PDF into a
# "Month Year" subfolder of a shared Drive folder instead of handing back a ZIP,
# so the team reads the records where they live rather than passing archives
# around. Authenticated as ONE FM's own service account - the same identity the
# Document Register uses - so the configured folder has to be shared with it.
# ---------------------------------------------------------------------------

# On Google Settings, per the work item. Note the upload still authenticates with the
# service account JSON on ONEFM General Setting - that is the identity the folder has to
# be shared with, not the OAuth client Google Settings configures.
DRIVE_FOLDER_DOCTYPE = "Google Settings"
DRIVE_FOLDER_SETTING = "pow_drive_folder_link"
DRIVE_FOLDER_MIME = "application/vnd.google-apps.folder"


def _configured_drive_folder() -> str:
	"""The Drive folder id the export uploads into, or "" when unconfigured.

	Accepts a share link or a bare id through the Document Register's reader, so the two
	places that take a Drive folder from a human agree on what a link is - a second
	regex here would be a second thing to get wrong.
	"""
	from one_fm.one_fm.doctype.document_register.document_register import _drive_id

	return _drive_id(
		frappe.db.get_single_value(DRIVE_FOLDER_DOCTYPE, DRIVE_FOLDER_SETTING)
	)


def _period_folder_name(start_date) -> str:
	"""``"July 2026"`` - the month the Proof of Work covers, not the month it was run."""
	return formatdate(start_date, "MMMM yyyy")


def _period_folder(service, parent_id: str, name: str) -> str:
	"""Id of the ``Month Year`` subfolder, creating it only if it is not there yet.

	Looked up by name under the parent rather than remembered anywhere: the folder is a
	place in someone's Drive, and it can be renamed, moved or recreated by hand between
	one month's export and the next.
	"""
	query = (
		f"name = '{name}' and mimeType = '{DRIVE_FOLDER_MIME}' "
		f"and '{parent_id}' in parents and trashed = false"
	)
	found = (
		service.files()
		.list(
			q=query,
			fields="files(id)",
			pageSize=1,
			supportsAllDrives=True,
			includeItemsFromAllDrives=True,
		)
		.execute()
	)
	files = found.get("files") or []
	if files:
		return files[0]["id"]

	created = (
		service.files()
		.create(
			body={"name": name, "mimeType": DRIVE_FOLDER_MIME, "parents": [parent_id]},
			fields="id",
			supportsAllDrives=True,
		)
		.execute()
	)
	return created["id"]


def _upload_pdf(service, folder_id: str, filename: str, content: bytes) -> str:
	"""Put one PDF in a Drive folder and return its id."""
	from googleapiclient.http import MediaIoBaseUpload

	media = MediaIoBaseUpload(io.BytesIO(content), mimetype="application/pdf", resumable=False)
	created = (
		service.files()
		.create(
			body={"name": filename, "parents": [folder_id]},
			media_body=media,
			fields="id",
			supportsAllDrives=True,
		)
		.execute()
	)
	return created["id"]


def _folder_link(folder_id: str) -> str:
	return f"https://drive.google.com/drive/folders/{folder_id}"


def _check_drive_folder(service, folder_id: str):
	"""Fail before the batch, saying what to do about it (WI-001981).

	Drive answers a folder it cannot write to with a bare
	"Insufficient permissions for the specified parent", raised from whichever contract
	happened to be first - a traceback that says nothing about which folder, which
	identity, or what to change. Asked once here instead, with the service account named,
	because sharing the folder with it is the fix and its address is not otherwise
	visible anywhere.
	"""
	from googleapiclient.errors import HttpError

	identity = google_credentials.service_account_email() or _("the service account")

	try:
		folder = (
			service.files()
			.get(
				fileId=folder_id,
				fields="name,driveId,capabilities(canAddChildren)",
				supportsAllDrives=True,
			)
			.execute()
		)
	except HttpError as exc:
		if exc.status_code == 404:
			frappe.throw(
				_(
					"The Proof of Work Drive folder ({0}) is not there, or is not shared with "
					"<b>{1}</b>. Share it with that address, or correct the folder on Google "
					"Settings."
				).format(folder_id, identity),
				title=_("Drive Folder Not Reachable"),
			)
		raise

	if not folder.get("capabilities", {}).get("canAddChildren"):
		frappe.throw(
			_(
				"<b>{0}</b> can see the Drive folder \"{1}\" but cannot write to it, so the "
				"month's subfolder cannot be created. Share the folder with that address as "
				"<b>Editor</b> (Content manager on a Shared Drive)."
			).format(identity, folder.get("name") or folder_id)
			+ ("" if folder.get("driveId") else "<br><br>" + _(
				"Note this folder lives in a personal My Drive. A service account has no "
				"storage of its own there, so uploads can still be refused for quota even "
				"once it can write - a <b>Shared Drive</b> is the arrangement that works."
			)),
			title=_("Drive Folder Not Writable"),
		)


def _upload_pow_pdfs(pow_names, user: str):
	"""Render each POW's merged PDF and upload it to Drive (WI-001981).

	One period subfolder per document rather than one for the batch: a batch is normally
	a single month, but nothing stops two periods being exported together, and a July
	record filed under August is worse than a second API call.

	A document that fails to render or upload is logged and skipped, the same contract
	the ZIP build keeps - one bad contract must not cost the others their upload.
	"""
	parent_id = _configured_drive_folder()
	service = google_credentials.get_drive_service()
	# Before anything is rendered: a folder that cannot be written to fails every
	# document in the batch, and the reason is the same one every time.
	_check_drive_folder(service, parent_id)

	folders = {}
	uploaded = []
	failed = []
	for pow_name in pow_names:
		try:
			doc = frappe.get_doc("Proof of Work", pow_name)
			period = _period_folder_name(doc.start_date)
			if period not in folders:
				folders[period] = _period_folder(service, parent_id, period)

			filename, content = _pow_pdf_entry(doc)
			_upload_pdf(service, folders[period], filename, content)
			uploaded.append(filename)
		except Exception:
			failed.append(pow_name)
			frappe.log_error(
				title="Proof of Work Drive upload failed",
				message=f"{pow_name}\n\n{frappe.get_traceback()}",
			)

	if not uploaded:
		_notify_zip(
			user,
			_("No Proof of Work PDF could be uploaded to Google Drive. Check the Error Log."),
		)
		return

	message = _("{0} Proof of Work PDF(s) uploaded to Google Drive.").format(len(uploaded))
	if failed:
		message += " " + _("{0} could not be uploaded - check the Error Log.").format(len(failed))

	# Straight to the period folder the PDFs are in, which is what the reader wants -
	# unless the batch spanned two periods, when there is no single one to send them to
	# and the parent is the only honest answer.
	destination = folders[next(iter(folders))] if len(folders) == 1 else parent_id

	_notify_zip(
		user, message, file_url=_folder_link(destination), link_label=_("Open Drive Folder")
	)


def _build_pow_zip(pow_names, user: str):
	"""Render one merged PDF per POW, ZIP them, and notify ``user`` when ready.

	Runs in a background job: each contract needs two wkhtmltopdf renders, so a full
	month would otherwise outlive the HTTP request. A contract that fails to render is
	logged and skipped rather than losing the whole archive.
	"""
	entries = []
	failed = []
	for pow_name in pow_names:
		try:
			doc = frappe.get_doc("Proof of Work", pow_name)
			entries.append(_pow_pdf_entry(doc))
		except Exception:
			failed.append(pow_name)
			frappe.log_error(
				title="Proof of Work ZIP render failed",
				message=f"{pow_name}\n\n{frappe.get_traceback()}",
			)

	if not entries:
		_notify_zip(user, _("No Proof of Work PDF could be rendered. Check the Error Log."))
		return

	content = _build_zip(entries)

	# The archive is delivered as a private File, so it is bounded by the site's
	# attachment limit (25 MB here). Say so plainly rather than letting the File
	# validation surface a raw framework error from inside a background job.
	from frappe.core.api.file import get_max_file_size

	max_size = get_max_file_size()
	if len(content) > max_size:
		_notify_zip(
			user,
			_(
				"The ZIP is {0} MB, over the {1} MB attachment limit. Generate fewer contracts at a time."
			).format(round(len(content) / 1048576, 1), round(max_size / 1048576)),
		)
		return

	# Private: a Proof of Work carries client attendance data and must not be public.
	zip_file = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"Proof-of-Work-{frappe.generate_hash(length=8)}.zip",
			"content": content,
			"is_private": 1,
		}
	).save()

	message = _("Your Proof of Work ZIP is ready: {0} file(s).").format(len(entries))
	if failed:
		message += " " + _("{0} could not be rendered - check the Error Log.").format(len(failed))

	_notify_zip(user, message, file_url=zip_file.unique_url)


def _notify_zip(user: str, message: str, file_url: str = None, link_label: str = None):
	"""Push the export outcome to the user who queued it.

	``msgprint`` over realtime is how this app already reports the result of a
	background job (see Item Request), and it renders the anchor as HTML.
	"""
	body = escape_html(message)
	if file_url:
		label = link_label or _("Download ZIP")
		body += f'<br><br><a href="{file_url}" target="_blank">{escape_html(label)}</a>'

	frappe.publish_realtime(event="msgprint", message=body, user=user)


@frappe.whitelist(methods=["POST"])
def enqueue_pow_zip(pow_names):
	"""Queue the ZIP build for a set of Proof of Work records (WI-001808).

	Returns immediately; the download link is pushed to the calling user over realtime
	once the archive is built.
	"""
	_guard_permission()

	if isinstance(pow_names, str):
		pow_names = frappe.parse_json(pow_names)

	if not pow_names:
		frappe.throw(_("No Proof of Work records to export."))

	# Only export what this user is allowed to read.
	for pow_name in pow_names:
		frappe.get_doc("Proof of Work", pow_name).check_permission("read")

	# WI-001981: Drive is the destination once a folder is configured. The ZIP stays as
	# the path for a site that has not set one - the alternative is a site whose export
	# button stops working until someone pastes a link, and the ZIP is what every site
	# has today.
	to_drive = bool(_configured_drive_folder())

	frappe.enqueue(
		_upload_pow_pdfs if to_drive else _build_pow_zip,
		queue="long",
		timeout=1500,
		pow_names=pow_names,
		user=frappe.session.user,
	)

	return {"queued": len(pow_names), "destination": "drive" if to_drive else "zip"}


if __name__ == "__main__":
	# Self-checks for the pure helpers (no Frappe context needed).
	blob = _build_zip([("a.pdf", b"AAA"), ("b.pdf", b"BBB")])
	with zipfile.ZipFile(io.BytesIO(blob)) as _zf:
		assert _zf.namelist() == ["a.pdf", "b.pdf"], _zf.namelist()
		assert _zf.read("b.pdf") == b"BBB"

	assert _safe_filename("A/B:C*D?") == "A B C D", _safe_filename("A/B:C*D?")
	assert _safe_filename("  spaced   out  ") == "spaced out"
	print("ok: _build_zip produced a valid 2-entry zip; _safe_filename scrubs separators")
