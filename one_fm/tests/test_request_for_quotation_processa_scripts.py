# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Request for Quotation process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


SCRIPTS = {
	"Assign Request for Quotation Step": """# Only a Purchase Manager can submit or cancel a Request for Quotation, so both steps go to that role.
result["assigned_user"] = ""
result["assigned_role"] = "Purchase Manager"
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
		"context_doctype": "Request for Quotation",
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


class TestAssignRequestForQuotationStep(FrappeTestCase):
	def test_steps_go_to_purchase_managers_only(self):
		doc = frappe.new_doc("Request for Quotation")
		doc.name = "RFQ-PROCESSA-TEST-1"
		result = run("Assign Request for Quotation Step", doc, assigned_role="Purchase Officer")
		self.assertEqual(result, {"assigned_user": "", "assigned_role": "Purchase Manager"})


class TestWorkflowStateField(FrappeTestCase):
	def test_the_map_has_a_field_to_write_the_state_to(self):
		field = frappe.get_meta("Request for Quotation").get_field("workflow_state")
		self.assertIsNotNone(field)
		self.assertEqual((field.fieldtype, field.options, field.no_copy, field.allow_on_submit), ("Link", "Workflow State", 1, 1))
