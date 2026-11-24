# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Subcontract Staff Request process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


SCRIPTS = {
	"Assign Subcontract Staff Request Step": """# Draft goes back to whoever raised the request. The review goes to the project's manager when
# that user is enabled and holds Projects Manager, else to every Projects Manager.
result["assigned_user"] = ""
result["assigned_role"] = ""
if doc.workflow_state == "Draft":
	result["assigned_user"] = doc.owner
elif doc.workflow_state == "Pending Project Manager":
	pm = doc.project_manager_user
	if pm and frappe.db.get_value("User", pm, "enabled") and "Projects Manager" in frappe.get_roles(pm):
		result["assigned_user"] = pm
	else:
		result["assigned_role"] = "Projects Manager"
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
		"context_doctype": "Subcontract Staff Request",
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


def user_with(role, holds=True):
	"""An enabled user who holds (or does not hold) the role."""
	holders = set(frappe.get_all("Has Role", filters={"role": role, "parenttype": "User"}, pluck="parent"))
	for u in frappe.get_all("User", filters={"enabled": 1, "user_type": "System User", "name": ["not in", ["Administrator", "Guest"]]}, pluck="name"):
		if (u in holders) == holds:
			return u


class TestAssignSubcontractStaffRequestStep(FrappeTestCase):
	def doc(self, state, pm=None):
		return frappe._dict(name="SSR-TEST", owner="owner@example.com", workflow_state=state, project_manager_user=pm)

	def test_draft_goes_to_owner(self):
		result = run("Assign Subcontract Staff Request Step", self.doc("Draft"))
		self.assertEqual(result, {"assigned_user": "owner@example.com", "assigned_role": ""})

	def test_review_goes_to_project_manager_holding_the_role(self):
		pm = user_with("Projects Manager")
		result = run("Assign Subcontract Staff Request Step", self.doc("Pending Project Manager", pm))
		self.assertEqual(result, {"assigned_user": pm, "assigned_role": ""})

	def test_review_falls_back_to_role(self):
		for pm in (None, user_with("Projects Manager", holds=False)):
			result = run("Assign Subcontract Staff Request Step", self.doc("Pending Project Manager", pm))
			self.assertEqual(result, {"assigned_user": "", "assigned_role": "Projects Manager"}, pm)

	def test_disabled_project_manager_falls_back_to_role(self):
		pm = user_with("Projects Manager")
		with patch("frappe.db.get_value", return_value=0):
			result = run("Assign Subcontract Staff Request Step", self.doc("Pending Project Manager", pm))
		self.assertEqual(result["assigned_role"], "Projects Manager")
