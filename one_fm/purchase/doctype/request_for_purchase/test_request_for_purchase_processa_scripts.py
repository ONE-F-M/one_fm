# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Request for Purchase process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


SCRIPTS = {
	"Route Request for Purchase": """# A Purchase Manager's own request goes straight to approval; any other goes to a Purchase Officer first.
result["to_purchase_manager"] = "Purchase Manager" in frappe.get_roles(doc.owner)
""",
	"Assign Request for Purchase Step": """# Opens the next step to every holder of the role that acts on it. A Draft goes back to its
# owner alone, so the role the previous step was given is cleared.
result["assigned_user"] = ""
result["assigned_role"] = {
	"Submit to Purchase Officer": "Purchase Officer",
	"Pending Approval": "Purchase Manager",
	"Approved": "Purchase Manager",
	"Rejected": "Purchase Manager",
}.get(doc.workflow_state, "")
""",
	"Validate Request for Purchase Cancel": """# Cancelling is refused while a Purchase Order made from this request is still open or approved.
# Sets result["step_valid"]; on False the process reopens the Approved task.
result["step_valid"] = True
if task_data.get("action") == "Cancel":
	orders = frappe.get_all(
		"Purchase Order",
		filters={"one_fm_request_for_purchase": doc.name, "docstatus": ("!=", 2)},
		pluck="name",
	)
	if orders:
		result["step_valid"] = False
		frappe.msgprint(
			frappe._("Cancel or delete these Purchase Orders first: {0}").format(", ".join(orders)),
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
		"context_doctype": "Request for Purchase",
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


def rfp(**kw):
	doc = frappe.new_doc("Request for Purchase")
	doc.name = "RFP-PROCESSA-TEST-1"
	doc.update(kw)
	return doc


class TestRouteRequestForPurchase(FrappeTestCase):
	def test_purchase_manager_goes_straight_to_approval(self):
		with patch("frappe.get_roles", return_value=["Purchase Manager", "Warehouse Supervisor"]):
			self.assertTrue(run("Route Request for Purchase", rfp(owner="pm@example.com"))["to_purchase_manager"])

	def test_anyone_else_goes_to_a_purchase_officer(self):
		with patch("frappe.get_roles", return_value=["Warehouse Supervisor"]) as roles:
			self.assertFalse(run("Route Request for Purchase", rfp(owner="ws@example.com"))["to_purchase_manager"])
		roles.assert_called_once_with("ws@example.com")


class TestAssignRequestForPurchaseStep(FrappeTestCase):
	def test_each_state_goes_to_its_role(self):
		for state, role in (("Submit to Purchase Officer", "Purchase Officer"), ("Pending Approval", "Purchase Manager"),
				("Approved", "Purchase Manager"), ("Rejected", "Purchase Manager")):
			self.assertEqual(run("Assign Request for Purchase Step", rfp(workflow_state=state))["assigned_role"], role, state)


class TestValidateRequestForPurchaseCancel(FrappeTestCase):
	def test_open_purchase_orders_block_the_cancel(self):
		with patch("frappe.get_all", return_value=["PO-1"]):
			self.assertFalse(run("Validate Request for Purchase Cancel", rfp(), action="Cancel")["step_valid"])

	def test_no_purchase_orders_let_it_cancel(self):
		with patch("frappe.get_all", return_value=[]):
			self.assertTrue(run("Validate Request for Purchase Cancel", rfp(), action="Cancel")["step_valid"])

	def test_cancelled_orders_are_not_counted(self):
		with patch("frappe.get_all", return_value=[]) as get_all:
			run("Validate Request for Purchase Cancel", rfp(), action="Cancel")
		self.assertEqual(get_all.call_args.kwargs["filters"]["docstatus"], ("!=", 2))
