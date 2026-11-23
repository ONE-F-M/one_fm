# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Supplier Quotation process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


SCRIPTS = {
	"Assign Supplier Quotation Step": """# A Purchase User submits the quotation; only a Purchase Manager can cancel it.
result["assigned_user"] = ""
result["assigned_role"] = {"Draft": "Purchase User", "Submitted": "Purchase Manager"}.get(doc.workflow_state, "")
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
		"context_doctype": "Supplier Quotation",
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


def sq(state):
	doc = frappe.new_doc("Supplier Quotation")
	doc.name = "SQ-PROCESSA-TEST-1"
	doc.workflow_state = state
	return doc


class TestAssignSupplierQuotationStep(FrappeTestCase):
	def test_a_purchase_user_submits(self):
		self.assertEqual(run("Assign Supplier Quotation Step", sq("Draft")), {"assigned_user": "", "assigned_role": "Purchase User"})

	def test_only_a_purchase_manager_cancels(self):
		self.assertEqual(run("Assign Supplier Quotation Step", sq("Submitted"))["assigned_role"], "Purchase Manager")

	def test_any_other_state_has_no_role(self):
		self.assertEqual(run("Assign Supplier Quotation Step", sq("Cancelled"))["assigned_role"], "")


class TestWorkflowStateField(FrappeTestCase):
	def test_the_map_has_a_field_to_write_the_state_to(self):
		from one_fm.custom.custom_field.supplier_quotation import get_supplier_quotation_custom_fields

		field = next(f for f in get_supplier_quotation_custom_fields()["Supplier Quotation"] if f["fieldname"] == "workflow_state")
		self.assertEqual((field["fieldtype"], field["options"], field["no_copy"], field["allow_on_submit"]), ("Link", "Workflow State", 1, 1))
