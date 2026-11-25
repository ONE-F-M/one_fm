# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Roster Employee Actions process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


SCRIPTS = {
	"Assign Roster Employee Action": """# The Site Supervisor User fixes the roster. A record with no Site Supervisor goes to the
# Project Manager User instead. These are the two Assignment Rules the process replaces.
# The process comes back here after any save of the record outside the engine; a status set
# to Completed by hand then ends the process and closes the task.
result["assigned_role"] = ""
result["assigned_user"] = (doc.site_supervisor_user if doc.site_supervisor else doc.project_manager_user) or ""
result["completed_by_hand"] = doc.status == "Completed"
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
		"context_doctype": "Roster Employee Actions",
		"context_docname": doc.name if doc else None,
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


class TestAssignRosterEmployeeAction(FrappeTestCase):
	def doc(self, **values):
		base = {"doctype": "Roster Employee Actions", "name": "test", "status": "Pending", "site_supervisor": "HR-EMP-1",
			"site_supervisor_user": "ss@example.com", "project_manager_user": "pm@example.com"}
		return frappe._dict({**base, **values})

	def test_site_supervisor_user_gets_the_task(self):
		result = run("Assign Roster Employee Action", self.doc())
		self.assertEqual(result["assigned_user"], "ss@example.com")
		self.assertEqual(result["assigned_role"], "")
		self.assertFalse(result["completed_by_hand"])

	def test_project_manager_user_when_there_is_no_site_supervisor(self):
		result = run("Assign Roster Employee Action", self.doc(site_supervisor=None, site_supervisor_user=None))
		self.assertEqual(result["assigned_user"], "pm@example.com")

	def test_site_supervisor_without_a_user_leaves_the_task_unassigned(self):
		result = run("Assign Roster Employee Action", self.doc(site_supervisor_user=None))
		self.assertEqual(result["assigned_user"], "")

	def test_status_completed_by_hand_ends_the_process(self):
		self.assertTrue(run("Assign Roster Employee Action", self.doc(status="Completed"))["completed_by_hand"])
