# Copyright (c) 2026, ONEFM and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, cstr, date_diff, flt, get_first_day, get_last_day, getdate

# Canonical values stored in the "Generation Basis" Select field.
GENERATION_BASIS_OPTIONS = ("Shift Hours", "Attendance Day", "Both")

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
# comes from planned post-days (Post Schedule) x hours-per-shift, mirroring the
# Sales Invoice logic; `actual_hours` and `staff_breakdown` come from the
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


def _planned_days_by_sale_item(contract_name: str, project: str, first_day, last_day) -> dict:
	"""
	Planned post-days per Sale Item, mirroring the Sales Invoice logic in
	``attendance_invoicing.generate_invoice_from_amendment``: only Service
	contract items, resolved through their Active Operations Roles -> Operations
	Posts -> Post Schedule rows with ``post_status == "Planned"`` in the period.

	Returns ``{sale_item: required_days}``.
	"""
	result = {}
	items = frappe.get_all(
		"Contract Item",
		filters={"parent": contract_name, "parenttype": "Contracts", "item_type": "Service"},
		fields=["item_code"],
	)
	for it in items:
		sale_item = it.item_code
		if not sale_item:
			continue

		roles = frappe.get_all(
			"Operations Role",
			filters={"project": project, "sale_item": sale_item, "status": "Active"},
			pluck="name",
		)
		if not roles:
			continue

		posts = frappe.get_all(
			"Operations Post",
			filters={"project": project, "post_template": ["in", roles], "status": "Active"},
			pluck="name",
		)
		if not posts:
			continue

		planned = frappe.db.count(
			"Post Schedule",
			{
				"project": project,
				"post": ["in", posts],
				"date": ["between", [first_day, last_day]],
				"post_status": "Planned",
			},
		)
		result[sale_item] = result.get(sale_item, 0) + planned

	return result


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


def _actual_hours(source: dict, shift_hours: float, basis: str) -> float:
	"""Hours worked for a Sale Item; falls back to present-days x shift hours
	when the source only carries statuses (no numeric hours)."""
	if basis == "Attendance Day":
		return flt(source.get("days", 0.0)) * shift_hours
	return flt(source.get("hours", 0.0)) or (flt(source.get("days", 0.0)) * shift_hours)


def _fmt_staff_breakdown(source: dict, shift_hours: float, basis: str) -> str:
	staff = source.get("staff", {})
	if not staff:
		return _("No attendance recorded for this item in the period.")

	lines = []
	for _key, info in sorted(staff.items(), key=lambda kv: (kv[1].get("name") or "", kv[0] or "")):
		label = info.get("name") or info.get("id") or _key
		prefix = f"{info.get('id')} - " if info.get("id") else ""
		hrs = _actual_hours(info, shift_hours, basis)
		lines.append(f"{prefix}{label}: {hrs:.2f} hrs")

	return "\n".join(lines)


def _populate_pow_items(doc, first_day, last_day):
	"""
	Fill the ``proof_of_work_item`` summary table on a POW document, one row per
	Sale Item, using the resolved data source. Called during generation only.

	contractual_hours = planned post-days (Post Schedule) x hours-per-shift.
	actual_hours      = hours worked from the resolved source.
	"""
	total_days = date_diff(last_day, first_day) + 1

	planned = _planned_days_by_sale_item(doc.contract, doc.project, first_day, last_day)

	source_type, reference = resolve_attendance_source(
		doc.contract, doc.project, getdate(first_day).month, getdate(first_day).year
	)
	if source_type == "amendment":
		source = _source_from_amendment(reference, total_days)
	else:
		source = _source_from_attendance(doc.project, first_day, last_day)

	basis = doc.generation_basis
	# Union of Sale Items with planned posts and/or actual attendance.
	sale_items = sorted(set(planned) | set(source))

	# Resolve item_type for all sale items in one query.
	item_types = {}
	if sale_items:
		for row in frappe.get_all(
			"Item", filters={"name": ["in", sale_items]}, fields=["name", "item_type"]
		):
			item_types[row.name] = row.item_type or ""

	doc.set("proof_of_work_item", [])
	for sale_item in sale_items:
		shift_hours = _shift_hours_from_item(sale_item)
		contractual_hours = flt(planned.get(sale_item, 0)) * shift_hours
		s_entry = source.get(sale_item, _blank_source_entry())

		doc.append(
			"proof_of_work_item",
			{
				"sale_item_code": sale_item,
				"item_type": item_types.get(sale_item, ""),
				"contractual_hours": f"{contractual_hours:.2f} hrs",
				"actual_hours": f"{_actual_hours(s_entry, shift_hours, basis):.2f} hrs",
				"staff_breakdown": _fmt_staff_breakdown(s_entry, shift_hours, basis),
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
def generate_proof_of_work(month: int, year: int, generation_basis: str, contracts):
	"""
	Batch-create one Proof of Work record per selected contract.

	Contracts that already have a POW for the period are skipped and
	reported back to the caller.
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

	for contract_name in contracts:
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

		doc.insert()

		created.append(doc.name)

	return {"created": created, "skipped": skipped}
