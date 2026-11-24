# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Subcontractor Contracts process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


SCRIPTS = {
	"Assign Subcontractor Contracts Step": """# Finance Managers activate and inactivate subcontractor contracts.
result["assigned_user"] = ""
result["assigned_role"] = "Finance Manager"
""",
	"Check Single Active Subcontractor Contract": """# A subcontractor has one Active contract at a time; billing reads its rates from it.
# Sets result["step_valid"]; on False the process reopens the task that asked for Active.
active = frappe.get_all(
	"Subcontractor Contracts",
	filters={"subcontractor_name": doc.subcontractor_name, "workflow_state": "Active", "name": ["!=", doc.name]},
	pluck="name",
)
result["step_valid"] = not active
if active:
	frappe.msgprint(
		frappe._("Subcontractor {0} already has an Active contract: {1}. Set it Inactive first.").format(doc.subcontractor_name, ", ".join(active)),
		title=frappe._("Active Contract Exists"),
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
		"context_doctype": "Subcontractor Contracts",
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


class TestSubcontractorContractsScripts(FrappeTestCase):
	def test_every_task_goes_to_finance_manager(self):
		doc = frappe._dict(name="SC-TEST")
		self.assertEqual(run("Assign Subcontractor Contracts Step", doc), {"assigned_user": "", "assigned_role": "Finance Manager"})

	def test_single_active_contract(self):
		doc = frappe._dict(name="SC-NEW", subcontractor_name="Sub")
		with patch("frappe.get_all", return_value=["SC-OLD"]) as get_all, patch("frappe.msgprint") as msg:
			result = {}
			namespace = {"frappe": frappe, "doc": doc, "task_data": {}, "result": result}
			exec(SCRIPTS["Check Single Active Subcontractor Contract"], namespace)
		self.assertEqual(result, {"step_valid": False})
		self.assertIn("SC-OLD", msg.call_args.args[0])
		self.assertEqual(get_all.call_args.kwargs["filters"], {"subcontractor_name": "Sub", "workflow_state": "Active", "name": ["!=", "SC-NEW"]})
		with patch("frappe.get_all", return_value=[]):
			self.assertEqual(run("Check Single Active Subcontractor Contract", doc), {"step_valid": True})
