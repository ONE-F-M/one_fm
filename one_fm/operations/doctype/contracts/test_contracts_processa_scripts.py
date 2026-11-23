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
# Month: the current month, or the previous month when the contract says so. A contract that
# fails is logged and the rest still run.
today = frappe.utils.getdate()
created, failed = [], []
contracts = frappe.get_all(
	"Contracts",
	filters={"workflow_state": "Active"},
	fields=["name", "due_date", "month_of_invoice"],
	order_by="name",
)
for contract in contracts:
	due = str(contract.due_date or "").strip()
	if due.lower() == "end of month":
		if today != frappe.utils.get_last_day(today):
			continue
	elif due != str(today.day):
		continue
	period = today if contract.month_of_invoice == "Current Month" else frappe.utils.add_months(today, -1)
	try:
		invoices = frappe.get_doc("Contracts", contract.name).generate_sales_invoice(period.month, period.year)
		if not isinstance(invoices, list):
			invoices = [invoices]
		created += [d.name for d in invoices if d]
	except Exception:
		failed.append(contract.name)
		frappe.log_error(title="Contracts Invoice: " + contract.name, message=frappe.get_traceback())
result["created"] = created
result["failed"] = failed
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
	def generate(self, today, contracts, failing=()):
		FakeContract.calls = []
		rows = [frappe._dict(name=n, due_date=d, month_of_invoice=m) for n, d, m in contracts]
		with patch("frappe.utils.getdate", return_value=getdate(today)), patch("frappe.get_all", return_value=rows), \
				patch("frappe.get_doc", side_effect=lambda dt, n: FakeContract(n, n in failing)), patch("frappe.log_error") as log:
			result = run("Generate Due Contract Invoices", frappe._dict(name=None))
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


class TestGeneratorSavesOnce(FrappeTestCase):
	def test_generator_does_not_save_after_insert(self):
		# A second save() wrote the stale workflow_state over the Draft the map sets on insert.
		import os

		with open(os.path.join(os.path.dirname(__file__), "contracts.py")) as f:
			self.assertNotIn("sales_invoice_doc.save()", f.read())
