# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Sales Invoice process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


SCRIPTS = {
	"Assign Sales Invoice Step": """# Opens the next step to every holder of the role that acts on it.
result["assigned_user"] = ""
result["assigned_role"] = {
	"Draft": "Accounts User",
	"Pending Approval from Operations Manager": "Operations Manager",
	"Approved by Operations Manager": "Accounts Manager",
	"Approved by Finance": "Accounts Manager",
	"Approved": "Accounts Manager",
}.get(doc.workflow_state, "")
""",
	"Check Sales Invoice Submission Requirements": """# The invoice needs the Client Confirmation Copy, and the Customer Purchase Order when its
# contract asks for one. Sets result["step_valid"]; on False the process reopens the Draft task.
missing = []
if not doc.custom_client_confirmation_copy:
	missing.append(frappe._("Client Confirmation Copy"))
if doc.contracts and not doc.po and frappe.db.get_value("Contracts", doc.contracts, "is_po_for_invoice"):
	missing.append(frappe._("Customer Purchase Order"))
result["step_valid"] = not missing
if missing:
	frappe.msgprint(
		frappe._("Please attach: {0}").format(", ".join(missing)),
		title=frappe._("Cannot Send for Approval"),
		indicator="red",
	)
""",
	"Assign Sales Invoice Collection Officer": """# When Accounts Additional Settings turns it on and names this state, assigns the invoice to the
# first Collection Officer so they deliver it and attach the delivered copy.
settings = frappe.get_doc("Accounts Additional Settings")
if (
	settings.assign_collection_officer_to_sales_invoice_on_workflow_state
	and doc.workflow_state == settings.sales_invoice_workflow_sate_to_assign_collection_officer
):
	officers = [
		user
		for user in frappe.get_all("Has Role", filters={"role": "Collection Officer", "parenttype": "User"}, pluck="parent", order_by="creation")
		if frappe.db.get_value("User", user, "enabled")
	]
	if not officers:
		frappe.log_error(title="Sales Invoice " + doc.name, message="No enabled user has the Collection Officer role.")
	elif not frappe.db.exists("ToDo", {"reference_type": doc.doctype, "reference_name": doc.name, "allocated_to": officers[0], "status": "Open"}):
		frappe.desk.form.assign_to.add({
			"doctype": doc.doctype,
			"name": doc.name,
			"assign_to": [officers[0]],
			"description": frappe._("The Sales Invoice {0} is ready for Delivery. Please attach the delivered invoice copy to the Sales Invoice.").format(doc.name),
		})
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
		"context_doctype": "Sales Invoice",
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


def si(**kw):
	doc = frappe.new_doc("Sales Invoice")
	doc.name = "SINV-PROCESSA-TEST-1"
	doc.update(kw)
	return doc


class TestAssignSalesInvoiceStep(FrappeTestCase):
	def test_each_state_goes_to_its_role(self):
		for state, role in (("Draft", "Accounts User"), ("Pending Approval from Operations Manager", "Operations Manager"),
				("Approved by Operations Manager", "Accounts Manager"), ("Approved by Finance", "Accounts Manager"), ("Approved", "Accounts Manager")):
			result = run("Assign Sales Invoice Step", si(workflow_state=state))
			self.assertEqual(result["assigned_role"], role, state)
			self.assertEqual(result["assigned_user"], "")


class TestCheckSalesInvoiceSubmissionRequirements(FrappeTestCase):
	def test_confirmation_copy_is_required(self):
		self.assertFalse(run("Check Sales Invoice Submission Requirements", si())["step_valid"])

	def test_copy_without_contract_passes(self):
		self.assertTrue(run("Check Sales Invoice Submission Requirements", si(custom_client_confirmation_copy="/files/c.pdf"))["step_valid"])

	def test_contract_asking_for_po_needs_it(self):
		with patch("frappe.db.get_value", return_value=1):
			self.assertFalse(run("Check Sales Invoice Submission Requirements", si(custom_client_confirmation_copy="/files/c.pdf", contracts="C-1"))["step_valid"])
			self.assertTrue(run("Check Sales Invoice Submission Requirements", si(custom_client_confirmation_copy="/files/c.pdf", contracts="C-1", po="/files/po.pdf"))["step_valid"])

	def test_contract_not_asking_for_po_passes(self):
		with patch("frappe.db.get_value", return_value=0):
			self.assertTrue(run("Check Sales Invoice Submission Requirements", si(custom_client_confirmation_copy="/files/c.pdf", contracts="C-1"))["step_valid"])


class TestAssignSalesInvoiceCollectionOfficer(FrappeTestCase):
	def settings(self, on, state):
		return frappe._dict(assign_collection_officer_to_sales_invoice_on_workflow_state=on, sales_invoice_workflow_sate_to_assign_collection_officer=state)

	def test_off_assigns_nobody(self):
		doc = si(workflow_state="Approved")
		with patch("frappe.get_doc", return_value=self.settings(0, "Approved")), patch("frappe.desk.form.assign_to.add") as add:
			run("Assign Sales Invoice Collection Officer", doc)
		add.assert_not_called()

	def test_on_assigns_first_enabled_officer(self):
		doc = si(workflow_state="Approved")
		with patch("frappe.get_doc", return_value=self.settings(1, "Approved")), \
				patch("frappe.get_all", return_value=["off@example.com", "co@example.com"]), \
				patch("frappe.db.get_value", side_effect=lambda dt, name, f: name == "co@example.com"), \
				patch("frappe.db.exists", return_value=False), patch("frappe.desk.form.assign_to.add") as add:
			run("Assign Sales Invoice Collection Officer", doc)
		self.assertEqual(add.call_args[0][0]["assign_to"], ["co@example.com"])

	def test_other_state_assigns_nobody(self):
		doc = si(workflow_state="Approved by Finance")
		with patch("frappe.get_doc", return_value=self.settings(1, "Approved")), patch("frappe.desk.form.assign_to.add") as add:
			run("Assign Sales Invoice Collection Officer", doc)
		add.assert_not_called()
