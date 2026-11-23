# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Purchase Invoice process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


SCRIPTS = {
	"Assign Purchase Invoice Step": """# Accounts Users submit and cancel Purchase Invoices, so both steps go to that role.
result["assigned_user"] = ""
result["assigned_role"] = "Accounts User"
""",
	"Check Linked Sales Invoices": """# Cancelling is refused while a submitted Sales Invoice rebills items from this Purchase Invoice.
# Sets result["step_valid"]; on False the process reopens the Submitted task.
linked = frappe.get_all(
	"Sales Invoice Item",
	filters={"custom_purchase_invoice": doc.name, "docstatus": 1},
	pluck="parent",
	distinct=True,
)
result["step_valid"] = not linked
if linked:
	frappe.msgprint(
		frappe._("Cannot cancel Purchase Invoice {0} as it is linked to submitted Sales Invoice(s): {1}").format(doc.name, ", ".join(linked)),
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
		"context_doctype": "Purchase Invoice",
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


def pi():
	doc = frappe.new_doc("Purchase Invoice")
	doc.name = "PINV-PROCESSA-TEST-1"
	return doc


class TestAssignPurchaseInvoiceStep(FrappeTestCase):
	def test_goes_to_accounts_users(self):
		result = run("Assign Purchase Invoice Step", pi())
		self.assertEqual((result["assigned_role"], result["assigned_user"]), ("Accounts User", ""))


class TestCheckLinkedSalesInvoices(FrappeTestCase):
	def test_submitted_sales_invoice_blocks_the_cancel(self):
		with patch("frappe.get_all", return_value=["SINV-1"]) as get_all:
			self.assertFalse(run("Check Linked Sales Invoices", pi())["step_valid"])
		self.assertEqual(get_all.call_args.kwargs["filters"], {"custom_purchase_invoice": "PINV-PROCESSA-TEST-1", "docstatus": 1})

	def test_no_linked_sales_invoice_lets_it_cancel(self):
		with patch("frappe.get_all", return_value=[]):
			self.assertTrue(run("Check Linked Sales Invoices", pi())["step_valid"])
