# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Proof of Work processes run as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one. The other Proof of Work tests read the rules from here through
rules(), and install_scripts() puts these bodies on the site for the hooks to run.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

# The Processa engine commits when an instance starts or fails. A test module starts this in
# setUpModule, so its records still roll back.
NO_COMMIT = patch("frappe.db.commit")

SCRIPTS = {
	"Populate Proof of Work Items": r"""# Fills a new Proof of Work from its contract and month: one manpower row per Service Sale Item
# of the contract (contracted, actual and staff breakdown, from an approved Attendance Amendment
# if there is one, else from Attendance), and the non-manpower contract lines rolled up per
# category. The Proof of Work Lifecycle map runs it right after the record is created, so a
# record made from the New form is filled the same way as one from the bulk generator.
# Source resolution, rate types and shift hours are shared with the Attendance Report print
# format, so they are imported from the Proof of Work module and both always agree.
from frappe import _
from frappe.utils import cint, date_diff, flt, getdate

from one_fm.one_fm.doctype.proof_of_work.proof_of_work import (
	PRESENT_STATUSES,
	_basis_for_rate_type,
	_contracted_count_by_sale_item,
	_item_types_by_sale_item,
	_num,
	_rate_type_by_sale_item,
	_shift_hours_from_item,
	resolve_attendance_source,
)

# The contractual justification assumes a standard month: a contracted head covers 30 days or
# 208 hours, whatever the shift length.
STANDARD_MONTH_DAYS = 30
STANDARD_MONTH_HOURS = 208


# Contracted amount per Contract Item Category for the non-manpower lines.
#
# The manpower tables cover Contract Items with Item Type "Service". "Items" rows are
# the non-manpower ones - annual maintenance, pest control, handyman and the like - and
# they carry no attendance, so there is nothing to count: they are reported as a
# contracted amount per category.
#
# ``item_code`` is blank on most of these rows in production, so the category is the
# only stable grouping key. ``rate`` is the figure that is consistently filled, with
# ``amount`` as the fallback where a row leaves it at zero.
#
# Returns ``[{"contract_item_category": str, "amount": float}, ...]`` ordered by
# category.
def _non_manpower_amount_by_category(contract_name: str) -> list:
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


# Fill the ``proof_of_work_items_nonmanpower`` rollup table on a POW document.
def _populate_pow_non_manpower_items(doc):
	doc.set("proof_of_work_items_nonmanpower", [])
	for row in _non_manpower_amount_by_category(doc.contract):
		doc.append("proof_of_work_items_nonmanpower", row)


# Whether hours come from the shift length rather than the clock.
#
# The update says an Hourly Sale Item "Fetch Shift Hours", which is the nominal length
# in the item code (``-12HR``) x days present - so the figures come out whole. Actual
# recorded working_hours are what produced values like 540.96, and they still drive the
# amendment path, where the data is shown as generated.
def _uses_nominal_shift_hours(rate_type: str, source_type: str) -> bool:
	return source_type != "amendment" and rate_type == "Hourly"


def _blank_source_entry() -> dict:
	return {"hours": 0.0, "days": 0.0, "staff": {}}


# Aggregate actual effort per Sale Item from an approved Attendance Amendment.
#
# Returns ``{sale_item: {"hours": float, "days": float, "staff": {...}}}``.
def _source_from_amendment(amendment_name: str, total_days: int) -> dict:
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


# Aggregate actual effort per Sale Item from standard Attendance records.
#
# Sale Item is resolved via the attendance's Operations Role. Returns
# ``{sale_item: {"hours": float, "days": float, "staff": {...}}}``.
def _source_from_attendance(project: str, first_day, last_day) -> dict:
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


# Group distinct staff by identical time worked for one metric.
#
# ``metric == "days"``  -> ``"- {n} Staff worked {v} days: {n*v} Days"``
# ``metric == "hours"`` -> ``"- {n} Staff worked {v} Hours: {n*v} Hrs"``
#
# Every distinct individual is counted (relievers included), so the group
# totals sum to the actual worked total even when head-count exceeds the
# contracted count. Hours fall back to days x shift length when no numeric
# hours were recorded.
def _group_breakdown(
	staff: dict, metric: str, shift_hours: float, nominal_shift_hours: bool = False
) -> str:
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


# Column 1: staff grouped by identical time worked. For "Both", the days
# breakdown, an "OR" line, then the hours breakdown.
def _fmt_staff_breakdown(
	source: dict, shift_hours: float, basis: str, nominal_shift_hours: bool = False
) -> str:
	staff = source.get("staff", {})
	if not staff:
		return _("No attendance recorded for this item in the period.")

	blocks = []
	if basis in ("Attendance Day", "Both"):
		blocks.append(_group_breakdown(staff, "days", shift_hours))
	if basis in ("Shift Hours", "Both"):
		blocks.append(_group_breakdown(staff, "hours", shift_hours, nominal_shift_hours))
	return "\nOR\n".join(b for b in blocks if b)


# Column 2: what was actually worked, in the metric the Rate Type asks for.
#
# The column is headed "Total number Days worked OR Total No of Hours worked", so a
# Daily or Monthly Sale Item belongs in days. It used to render hours unconditionally -
# and for those Rate Types the hours were days x the shift length, so a 344-day month
# printed as "4128.00 hrs" beside a contractual figure quoted in DAYS.
#
# Split on basis like the two columns either side of it, so all three of a row's
# figures are in the same unit.
def _fmt_actual(
	source: dict, shift_hours: float, basis: str, nominal_shift_hours: bool = False
) -> str:
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


# Column 3: contracted head-count x the standard month. For "Both", the days
# justification, an "OR" line, then the hours justification.
def _fmt_contractual(count: int, basis: str) -> str:
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


# Fill the ``proof_of_work_item`` summary table on a POW document, one row per
# Sale Item, using the resolved data source. Called during generation only.
#
# contractual_hours = contracted head-count (Contract Item `count`) x the
#                     standard month (30 days / 208 hours), per generation basis.
# actual_hours      = hours worked from the resolved source.
# staff_breakdown   = distinct staff grouped by identical time worked.
def _populate_pow_items(doc, first_day, last_day):
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



# Only a record not yet filled, so items edited by hand before a later step are kept.
if bpmn_id and doc.get("doctype") == "Proof of Work" and doc.start_date and doc.end_date and not doc.proof_of_work_item:
	_populate_pow_items(doc, getdate(doc.start_date), getdate(doc.end_date))
	_populate_pow_non_manpower_items(doc)
	doc.save()
result["items_filled"] = bool(doc.get("proof_of_work_item"))
""",
}


class Rules:
	"""A script's functions and constants as attributes. The attributes are the script's own
	namespace, so patching one (patch.object(rules, "fn")) also changes what the other
	functions of the script call."""


def rules(script_name):
	"""The functions and constants a script defines, without taking its map step."""
	namespace = {"frappe": frappe, "doc": frappe._dict(), "task_data": {}, "result": {},
		"context_doctype": "", "context_docname": "", "bpmn_id": ""}
	exec(SCRIPTS[script_name], namespace)
	found = Rules()
	found.__dict__ = namespace
	return found


def run(script_name, doc=None, **task_data):
	"""Run a script the way the Processa engine does, as a map step, and return its result."""
	result = {}
	namespace = {
		"frappe": frappe,
		"doc": doc or frappe._dict(),
		"task_data": task_data,
		"result": result,
		"context_doctype": doc.doctype if doc else "",
		"context_docname": doc.name if doc else "",
		"bpmn_id": "test",
	}
	namespace.update(task_data)
	exec(SCRIPTS[script_name], namespace)
	return result


def install_scripts():
	"""Put these bodies on the site, so the hooks under test run the reviewed scripts."""
	for name, body in SCRIPTS.items():
		if frappe.db.exists("Server Script", name):
			frappe.db.set_value("Server Script", name, {"script": body, "disabled": 0}, update_modified=False)
		else:
			frappe.get_doc({"doctype": "Server Script", "name": name, "script_type": "API",
				"api_method": frappe.scrub(name), "script": body}).db_insert()


class TestSiteScripts(FrappeTestCase):
	def test_site_scripts_match_this_file(self):
		for name, body in SCRIPTS.items():
			saved = frappe.db.get_value("Server Script", name, "script")
			if saved is not None:
				self.assertEqual(saved.strip(), body.strip(), msg=name)
