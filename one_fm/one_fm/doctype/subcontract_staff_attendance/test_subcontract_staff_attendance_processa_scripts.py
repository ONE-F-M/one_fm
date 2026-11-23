# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Subcontract Staff Attendance process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase


SCRIPTS = {
	"Validate Remarks": """# Checks the remarks a return or a dispute needs before the process moves the record on.
# Sets result["step_valid"]; on False the process reopens the same task.
action = task_data.get("action")
error = None
if action in ("Return To Draft", "Return To Subcontractor"):
	if not any(row.remarks for row in doc.subcontractor_staff_attendance_item):
		error = "You must provide a remark for at least one employee when returning the document to Draft."
elif action == "Raise Dispute" and not doc.remarks_from_operations_supervisor:
	error = "Please provide Remarks from Operations Supervisor before raising a dispute."
elif action == "Return To Operations Supervisor" and not doc.remarks_from_projects_manager:
	error = "Please provide Remarks from Projects Manager before returning the document to Operations Supervisor."

result["step_valid"] = not error
if error:
	frappe.msgprint(frappe._(error), title=frappe._("Remarks Required"), indicator="red")
""",
	"Assign Subcontractor Billing Step": """# Accounts Users create the subcontractor's Purchase Invoice.
result["assigned_user"] = ""
result["assigned_role"] = "Accounts User"
""",
	"Generate Subcontractor Billing": """# Creates the subcontractor's Purchase Invoice for this approved record, once per record.
# Each employee's Operations Role gives the Sale Item; the Active Subcontractor Contract gives its
# rate type, rate and count. Monthly items bill worked days / days in the period, Daily items bill days.
# Sets result["step_valid"]; on False the process reopens the Create Purchase Invoice task.
# The new invoice starts its own Purchase Invoice Lifecycle: Draft, then an Accounts User submits it.
errors = []
invoice = frappe.db.get_value(
	"Purchase Invoice",
	{"custom_subcontract_attendance_reference": doc.name, "docstatus": ["<", 2]},
	"name",
)
contract = None
if not invoice:
	contract = frappe.db.get_value(
		"Subcontractor Contracts",
		{"subcontractor_name": doc.subcontractor_name, "workflow_state": "Active"},
		"name",
	)
	if not contract:
		errors.append(frappe._("No Active Subcontractor Contract found for {0}.").format(doc.subcontractor_name))

if contract:
	terms = {row.item_code: row for row in frappe.get_doc("Subcontractor Contracts", contract).subcontractor_items}
	worked = {}
	for row in doc.subcontractor_staff_attendance_item:
		role = frappe.db.get_value("Employee", row.employee, "custom_operations_role_allocation")
		item_code = frappe.db.get_value("Operations Role", role, "sale_item") if role else None
		if not role:
			errors.append(frappe._("Employee {0} has no Operations Role Allocation.").format(row.employee))
		elif not item_code:
			errors.append(frappe._("Operations Role {0} has no Sale Item.").format(role))
		elif item_code not in terms:
			errors.append(frappe._("Item {0} (employee {1}) is not on Subcontractor Contract {2}.").format(item_code, row.employee, contract))
		else:
			worked[item_code] = worked.get(item_code, 0) + frappe.utils.flt(row.working_days)

	period_days = frappe.utils.date_diff(doc.to_date, doc.from_date) + 1
	items = []
	for item_code, days in worked.items():
		term = terms[item_code]
		qty = days / period_days if term.rate_type == "Monthly" else days
		if term.rate_type == "Monthly" and qty > term.count:
			errors.append(frappe._("Can not bill more than the contract count for item {0} ({1} > {2}).").format(item_code, frappe.utils.flt(qty, 2), term.count))
		if qty:
			items.append({"item_code": item_code, "qty": qty, "rate": term.rate})
	if not items and not errors:
		errors.append(frappe._("No worked days to bill on this attendance record."))

	if not errors:
		pi = frappe.new_doc("Purchase Invoice")
		pi.update({
			"company": frappe.defaults.get_user_default("Company") or frappe.db.get_single_value("Global Defaults", "default_company"),
			"supplier": doc.subcontractor_name,
			"set_posting_time": 1,
			"posting_date": frappe.utils.today(),
			"bill_date": doc.to_date,
			"is_subcontracted": 1,
			"custom_subcontract_attendance_reference": doc.name,
			"items": items,
		})
		try:
			pi.insert()
			invoice = pi.name
		except frappe.ValidationError:
			# The invoice's own validation has already shown why, e.g. Purchase Order Required.
			errors.append(frappe._("The Purchase Invoice could not be created."))

result["step_valid"] = not errors
if invoice:
	result["purchase_invoice"] = invoice
	frappe.msgprint(frappe._("Purchase Invoice {0} is ready for submission.").format(invoice), indicator="green")
for e in errors:
	frappe.msgprint(e, title=frappe._("Cannot Create Purchase Invoice"), indicator="red")
""",
	"Assign Subcontract Staff Attendance Cancel Step": """# System Managers cancel an approved attendance record.
result["assigned_user"] = ""
result["assigned_role"] = "System Manager"
""",
	"Check Subcontract Staff Attendance Cancel": """# Refuses Cancel while a Purchase Invoice made from this record is not cancelled.
# Sets result["step_valid"]; on False the process reopens the Cancel task.
invoice = frappe.db.get_value(
	"Purchase Invoice",
	{"custom_subcontract_attendance_reference": doc.name, "docstatus": ["<", 2]},
	"name",
)
result["step_valid"] = not invoice
if invoice:
	frappe.msgprint(
		frappe._("Cancel Purchase Invoice {0} first.").format(invoice),
		title=frappe._("Cannot Cancel"),
		indicator="red",
	)
""",
}


def run(script_name, doc, **task_data):
	"""Run a script the way the Processa engine does and return its result."""
	result = {}
	namespace = {
		"frappe": frappe,
		"doc": doc,
		"task_data": task_data,
		"result": result,
		"context_doctype": "Subcontract Staff Attendance",
		"context_docname": doc.name,
		"bpmn_id": "test",
	}
	with patch("frappe.msgprint"):
		exec(SCRIPTS[script_name], namespace)
	return result


class TestSiteScripts(FrappeTestCase):
	def test_site_scripts_match_this_file(self):
		for name, body in SCRIPTS.items():
			saved = frappe.db.get_value("Server Script", name, "script")
			if saved is None:
				continue
			self.assertEqual(saved.strip(), body.strip(), name)


DT = "Subcontract Staff Attendance"


def attendance(**kw):
	doc = frappe.new_doc(DT)
	doc.name = "SSA-PROCESSA-TEST-1"
	doc.update({"subcontractor_name": "_Test Supplier", "from_date": "2025-01-01", "to_date": "2025-01-31"})
	doc.update(kw)
	return doc


def with_rows(*remarks, **kw):
	doc = attendance(**kw)
	for i, r in enumerate(remarks):
		doc.append("subcontractor_staff_attendance_item", {"employee": f"EMP-{i}", "remarks": r, "working_days": "20"})
	return doc


class TestValidateRemarks(FrappeTestCase):
	def test_returns_need_an_employee_remark(self):
		for action in ("Return To Draft", "Return To Subcontractor"):
			self.assertFalse(run("Validate Remarks", with_rows(None, ""), action=action)["step_valid"], action)
			self.assertTrue(run("Validate Remarks", with_rows(None, "Day 3"), action=action)["step_valid"], action)

	def test_dispute_needs_supervisor_remarks(self):
		self.assertFalse(run("Validate Remarks", attendance(), action="Raise Dispute")["step_valid"])
		self.assertTrue(run("Validate Remarks", attendance(remarks_from_operations_supervisor="x"), action="Raise Dispute")["step_valid"])

	def test_return_to_supervisor_needs_manager_remarks(self):
		self.assertFalse(run("Validate Remarks", attendance(), action="Return To Operations Supervisor")["step_valid"])
		self.assertTrue(run("Validate Remarks", attendance(remarks_from_projects_manager="x"), action="Return To Operations Supervisor")["step_valid"])

	def test_approve_needs_nothing(self):
		self.assertTrue(run("Validate Remarks", attendance(), action="Approve")["step_valid"])


class TestAssignSteps(FrappeTestCase):
	def test_roles(self):
		self.assertEqual(run("Assign Subcontractor Billing Step", attendance())["assigned_role"], "Accounts User")
		self.assertEqual(run("Assign Subcontract Staff Attendance Cancel Step", attendance())["assigned_role"], "System Manager")


class TestCheckCancel(FrappeTestCase):
	def test_open_invoice_blocks_the_cancel(self):
		with patch("frappe.db.get_value", return_value="PINV-1") as get_value:
			self.assertFalse(run("Check Subcontract Staff Attendance Cancel", attendance())["step_valid"])
		self.assertEqual(get_value.call_args.args[1], {"custom_subcontract_attendance_reference": "SSA-PROCESSA-TEST-1", "docstatus": ["<", 2]})

	def test_no_open_invoice_lets_it_cancel(self):
		with patch("frappe.db.get_value", return_value=None):
			self.assertTrue(run("Check Subcontract Staff Attendance Cancel", attendance())["step_valid"])


class TestGenerateSubcontractorBilling(FrappeTestCase):
	def values(self, invoice=None, contract="CON-1", role="ROLE-1", item="ITEM-1"):
		table = {"Purchase Invoice": invoice, "Subcontractor Contracts": contract, "Employee": role, "Operations Role": item}
		return lambda doctype, *a, **k: table[doctype]

	def contract(self, rate_type="Monthly", count=2):
		return frappe._dict(subcontractor_items=[frappe._dict(item_code="ITEM-1", rate_type=rate_type, count=count, rate=310)])

	def test_existing_invoice_is_returned_not_duplicated(self):
		doc = with_rows("", "")
		with patch("frappe.db.get_value", side_effect=self.values(invoice="PINV-1")), patch("frappe.new_doc") as new_doc:
			result = run("Generate Subcontractor Billing", doc)
		self.assertEqual((result["purchase_invoice"], result["step_valid"]), ("PINV-1", True))
		new_doc.assert_not_called()

	def test_no_active_contract_is_a_gate(self):
		doc = with_rows("")
		with patch("frappe.db.get_value", side_effect=self.values(contract=None)), patch("frappe.new_doc") as new_doc:
			result = run("Generate Subcontractor Billing", doc)
		self.assertFalse(result["step_valid"])
		new_doc.assert_not_called()

	def test_monthly_bills_worked_days_over_period_days(self):
		pi = MagicMock()
		pi.name = "PINV-NEW"
		doc = with_rows("", "")
		with patch("frappe.db.get_value", side_effect=self.values()), patch("frappe.get_doc", return_value=self.contract()), \
			patch("frappe.new_doc", return_value=pi):
			result = run("Generate Subcontractor Billing", doc)
		self.assertTrue(result["step_valid"])
		self.assertEqual(result["purchase_invoice"], "PINV-NEW")
		self.assertEqual(pi.update.call_args.args[0]["custom_subcontract_attendance_reference"], "SSA-PROCESSA-TEST-1")
		self.assertAlmostEqual(pi.update.call_args.args[0]["items"][0]["qty"], 40 / 31)

	def test_daily_bills_worked_days_without_a_count_cap(self):
		pi = MagicMock()
		pi.name = "PINV-NEW"
		doc = with_rows("", "")
		with patch("frappe.db.get_value", side_effect=self.values()), patch("frappe.get_doc", return_value=self.contract("Daily", 1)), \
			patch("frappe.new_doc", return_value=pi):
			result = run("Generate Subcontractor Billing", doc)
		self.assertTrue(result["step_valid"])
		self.assertEqual(pi.update.call_args.args[0]["items"][0]["qty"], 40)

	def test_monthly_over_the_contract_count_is_a_gate(self):
		doc = with_rows("", "")
		with patch("frappe.db.get_value", side_effect=self.values()), patch("frappe.get_doc", return_value=self.contract("Monthly", 1)), \
			patch("frappe.new_doc") as new_doc:
			result = run("Generate Subcontractor Billing", doc)
		self.assertFalse(result["step_valid"])
		new_doc.assert_not_called()

	def test_invoice_validation_error_is_a_gate(self):
		pi = MagicMock()
		pi.insert.side_effect = frappe.ValidationError("Purchase Order Required")
		doc = with_rows("", "")
		with patch("frappe.db.get_value", side_effect=self.values()), patch("frappe.get_doc", return_value=self.contract()), \
			patch("frappe.new_doc", return_value=pi):
			result = run("Generate Subcontractor Billing", doc)
		self.assertFalse(result["step_valid"])
		self.assertNotIn("purchase_invoice", result)
