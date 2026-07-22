# Copyright (c) 2026, ONEFM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_first_day, get_last_day, getdate

# Canonical values stored in the "Generation Basis" Select field.
GENERATION_BASIS_OPTIONS = ("Shift Hours", "Attendance Day", "Both")


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
		doc.insert()

		created.append(doc.name)

	return {"created": created, "skipped": skipped}
