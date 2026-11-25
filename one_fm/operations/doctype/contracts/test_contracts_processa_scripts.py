# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Contracts process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


SCRIPTS = {
	"Generate Due Contract Invoices": """# Runs daily. For every Active contract whose Invoice Submission Due Date is today (or End of
# Month on the month's last day), generates the Sales Invoice(s) for the Invoice Submission
# Month: the current month, or the previous month when the contract says so.
# Invoice Frequency, as the old 03:12 job read it: Monthly (or blank) bills on every due date.
# Quarterly bills only when the full months since the contract Start Date, plus one, divide by 3,
# and then bills the three months up to the Invoice Submission Month. Yearly is not billed here.
# A contract is skipped when it already has a Sales Invoice that is not cancelled for the period:
# one whose From Date falls in it, or one with no From Date posted this month (the Generate Sales
# Invoice button and this job set no From Date). A contract that fails is logged and the rest run.
today = frappe.utils.getdate()
month_start, month_end = frappe.utils.get_first_day(today), frappe.utils.get_last_day(today)
created, failed, skipped = [], [], []
contracts = frappe.get_all(
	"Contracts",
	filters={"workflow_state": "Active"},
	fields=["name", "due_date", "month_of_invoice", "invoice_frequency", "start_date"],
	order_by="name",
)
for contract in contracts:
	due = str(contract.due_date or "").strip()
	if due.lower() == "end of month":
		if today != month_end:
			continue
	elif due != str(today.day):
		continue
	period = today if contract.month_of_invoice == "Current Month" else frappe.utils.add_months(today, -1)
	months = [period]
	if contract.invoice_frequency == "Quarterly":
		if not contract.start_date:
			continue
		start = frappe.utils.getdate(contract.start_date)
		full_months = (today.year - start.year) * 12 + today.month - start.month
		if frappe.utils.add_months(start, full_months) > today:
			full_months -= 1
		if (full_months + 1) % 3:
			continue
		months = [frappe.utils.add_months(period, -2), frappe.utils.add_months(period, -1), period]
	elif contract.invoice_frequency not in (None, "", "Monthly"):
		continue
	billed = {"contracts": contract.name, "docstatus": ["<", 2]}
	for_period = dict(billed, from_date=["between", [frappe.utils.get_first_day(months[0]), frappe.utils.get_last_day(period)]])
	this_month = dict(billed, from_date=["is", "not set"], posting_date=["between", [month_start, month_end]])
	if frappe.db.exists("Sales Invoice", for_period) or frappe.db.exists("Sales Invoice", this_month):
		skipped.append(contract.name)
		continue
	try:
		for month in months:
			invoices = frappe.get_doc("Contracts", contract.name).generate_sales_invoice(month.month, month.year)
			if not isinstance(invoices, list):
				invoices = [invoices]
			created += [d.name for d in invoices if d]
	except Exception:
		failed.append(contract.name)
		frappe.log_error(title="Contracts Invoice: " + contract.name, message=frappe.get_traceback())
result["created"] = created
result["failed"] = failed
result["skipped"] = skipped
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
		"context_doctype": "Contracts",
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


from frappe.utils import getdate


class FakeContract:
	calls = []

	def __init__(self, name, fail=False):
		self.name, self.fail = name, fail

	def generate_sales_invoice(self, month, year):
		FakeContract.calls.append((self.name, month, year))
		if self.fail:
			raise frappe.ValidationError("Post Schedule missing")
		return frappe._dict(name="SINV-" + self.name)


class TestGenerateDueContractInvoices(FrappeTestCase):
	def generate(self, today, contracts, failing=(), billed=()):
		"""contracts: (name, due_date, month_of_invoice[, invoice_frequency[, start_date]])"""
		FakeContract.calls = []
		rows = []
		for c in contracts:
			c = tuple(c) + (None,) * (5 - len(c))
			rows.append(frappe._dict(name=c[0], due_date=c[1], month_of_invoice=c[2], invoice_frequency=c[3], start_date=c[4] and getdate(c[4])))
		exists_calls = []

		def exists(dt, filters):
			exists_calls.append(filters)
			return filters["contracts"] in billed

		with patch("frappe.utils.getdate", side_effect=lambda d=None: getdate(d) if d else getdate(today)), \
				patch("frappe.get_all", return_value=rows), patch("frappe.db.exists", side_effect=exists), \
				patch("frappe.get_doc", side_effect=lambda dt, n: FakeContract(n, n in failing)), patch("frappe.log_error") as log:
			result = run("Generate Due Contract Invoices", frappe._dict(name=None))
		self.exists_calls = exists_calls
		return result, FakeContract.calls, log

	def test_bills_contracts_due_today_for_their_month(self):
		result, calls, _log = self.generate("2026-11-05", [("A", "5", "Current Month"), ("B", "5", "Previous Month"), ("C", "6", "Current Month")])
		self.assertEqual(calls, [("A", 11, 2026), ("B", 10, 2026)])
		self.assertEqual(result["created"], ["SINV-A", "SINV-B"])

	def test_previous_month_in_january_is_last_december(self):
		_result, calls, _log = self.generate("2027-01-05", [("A", "5", "Previous Month")])
		self.assertEqual(calls, [("A", 12, 2026)])

	def test_end_of_month_only_on_the_last_day(self):
		_r, calls, _l = self.generate("2026-11-29", [("A", "End of Month", "Current Month")])
		self.assertEqual(calls, [])
		_r, calls, _l = self.generate("2026-11-30", [("A", "End of Month", "Current Month")])
		self.assertEqual(calls, [("A", 11, 2026)])

	def test_a_failing_contract_is_logged_and_the_rest_run(self):
		result, calls, log = self.generate("2026-11-05", [("A", "5", "Current Month"), ("B", "5", "Current Month")], failing=("A",))
		self.assertEqual([c[0] for c in calls], ["A", "B"])
		self.assertEqual(result["failed"], ["A"])
		self.assertEqual(result["created"], ["SINV-B"])
		self.assertEqual(log.call_count, 1)

	def test_monthly_and_blank_frequency_bill_every_due_date_yearly_does_not(self):
		_r, calls, _l = self.generate("2026-11-05", [("A", "5", "Current Month", "Monthly"), ("B", "5", "Current Month", ""), ("C", "5", "Current Month", "Yearly")])
		self.assertEqual(calls, [("A", 11, 2026), ("B", 11, 2026)])

	def test_quarterly_bills_three_months_when_the_old_job_did(self):
		# Started 2026-01-10: on 2026-03-10 two full months have passed, plus one makes 3.
		_r, calls, _l = self.generate("2026-03-10", [("Q", "10", "Current Month", "Quarterly", "2026-01-10")])
		self.assertEqual(calls, [("Q", 1, 2026), ("Q", 2, 2026), ("Q", 3, 2026)])
		self.assertEqual(self.exists_calls[0]["from_date"], ["between", [getdate("2026-01-01"), getdate("2026-03-31")]])
		_r, calls, _l = self.generate("2026-03-10", [("Q", "10", "Previous Month", "Quarterly", "2026-01-10")])
		self.assertEqual(calls, [("Q", 12, 2025), ("Q", 1, 2026), ("Q", 2, 2026)])

	def test_quarterly_skips_the_other_months(self):
		for today in ("2026-02-10", "2026-04-10", "2026-05-10"):
			_r, calls, _l = self.generate(today, [("Q", "10", "Current Month", "Quarterly", "2026-01-10")])
			self.assertEqual(calls, [], today)
		# One day short of the third full month still counts two, as relativedelta did.
		_r, calls, _l = self.generate("2026-03-09", [("Q", "9", "Current Month", "Quarterly", "2026-01-10")])
		self.assertEqual(calls, [])
		_r, calls, _l = self.generate("2026-06-10", [("Q", "10", "Current Month", "Quarterly", "2026-01-10")])
		self.assertEqual(len(calls), 3)

	def test_quarterly_without_start_date_is_not_billed(self):
		_r, calls, _l = self.generate("2026-03-10", [("Q", "10", "Current Month", "Quarterly", None)])
		self.assertEqual(calls, [])

	def test_contract_already_billed_for_the_period_is_skipped(self):
		result, calls, _l = self.generate("2026-11-05", [("A", "5", "Current Month"), ("B", "5", "Current Month")], billed=("A",))
		self.assertEqual(calls, [("B", 11, 2026)])
		self.assertEqual(result["skipped"], ["A"])

	def test_billed_check_covers_the_period_and_this_months_undated_invoices(self):
		self.generate("2026-11-05", [("B", "5", "Previous Month")])
		for_period, this_month = self.exists_calls
		self.assertEqual(for_period, {"contracts": "B", "docstatus": ["<", 2], "from_date": ["between", [getdate("2026-10-01"), getdate("2026-10-31")]]})
		self.assertEqual(this_month, {"contracts": "B", "docstatus": ["<", 2], "from_date": ["is", "not set"], "posting_date": ["between", [getdate("2026-11-01"), getdate("2026-11-30")]]})


class TestGeneratorSavesOnce(FrappeTestCase):
	def test_generator_does_not_save_after_insert(self):
		# A second save() wrote the stale workflow_state over the Draft the map sets on insert.
		import os

		with open(os.path.join(os.path.dirname(__file__), "contracts.py")) as f:
			self.assertNotIn("sales_invoice_doc.save()", f.read())
