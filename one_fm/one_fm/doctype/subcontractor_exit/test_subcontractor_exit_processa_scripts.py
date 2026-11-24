# Copyright (c) 2026, ONE FM and Contributors
# See license.txt
"""The Server Scripts the Subcontractor Exit process runs as script tasks.

The scripts live on the site and move between sites with the process export, so their
bodies are mirrored here. test_site_scripts_match_this_file catches a site copy that has
drifted from the reviewed one.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


SCRIPTS = {
	"Assign Subcontractor Exit Step": """# Draft goes back to whoever raised the exit. The approval goes to the Operations Manager User
# (End Services) or the Project Manager User (Reduce Staff) when that user is enabled and holds
# the role, else to every holder of the role. Later steps go to every holder of their role.
result["assigned_user"] = ""
result["assigned_role"] = ""
approver = {
	"Pending Operations Manager": (doc.operations_manager_user, "Operations Manager"),
	"Pending Project Manager": (doc.project_manager_user, "Projects Manager"),
}.get(doc.workflow_state)
if doc.workflow_state == "Draft":
	result["assigned_user"] = doc.owner
elif approver:
	user, role = approver
	if user and frappe.db.get_value("User", user, "enabled") and role in frappe.get_roles(user):
		result["assigned_user"] = user
	else:
		result["assigned_role"] = role
else:
	result["assigned_role"] = {
		"Pending GSD Supervisor": "Accommodation User",
		"Pending Offboarding Officer": "Offboarding Officer",
		"Pending Finance Manager": "Finance Manager",
	}.get(doc.workflow_state, "")
""",
	"Fill Subcontractor Exit Defaults": """# Requested By is whoever raised the exit; the Operations Manager User defaults to the
# Default Operation Manager in Operation Settings.
values = {}
if not doc.requested_by:
	values["requested_by"] = doc.owner
if not doc.operations_manager_user:
	default_manager = frappe.db.get_single_value("Operation Settings", "default_operation_manager")
	if default_manager:
		values["operations_manager_user"] = default_manager
if values:
	frappe.db.set_value("Subcontractor Exit", doc.name, values, update_modified=False)
	result.update(values)
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
		"context_doctype": "Subcontractor Exit",
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


def user_with(role):
	holders = frappe.get_all("Has Role", filters={"role": role, "parenttype": "User", "parent": ["not in", ["Administrator", "Guest"]]}, pluck="parent")
	return next(u for u in holders if frappe.db.get_value("User", u, "enabled"))


class TestAssignSubcontractorExitStep(FrappeTestCase):
	def doc(self, state, om=None, pm=None):
		return frappe._dict(name="SE-TEST", owner="owner@example.com", workflow_state=state, operations_manager_user=om, project_manager_user=pm)

	def test_draft_goes_to_owner(self):
		self.assertEqual(run("Assign Subcontractor Exit Step", self.doc("Draft")), {"assigned_user": "owner@example.com", "assigned_role": ""})

	def test_approvers_by_user_field_or_role(self):
		om, pm = user_with("Operations Manager"), user_with("Projects Manager")
		self.assertEqual(run("Assign Subcontractor Exit Step", self.doc("Pending Operations Manager", om=om))["assigned_user"], om)
		self.assertEqual(run("Assign Subcontractor Exit Step", self.doc("Pending Project Manager", pm=pm))["assigned_user"], pm)
		self.assertEqual(run("Assign Subcontractor Exit Step", self.doc("Pending Operations Manager")), {"assigned_user": "", "assigned_role": "Operations Manager"})
		self.assertEqual(run("Assign Subcontractor Exit Step", self.doc("Pending Project Manager")), {"assigned_user": "", "assigned_role": "Projects Manager"})

	def test_later_steps_go_to_roles(self):
		for state, role in (("Pending GSD Supervisor", "Accommodation User"), ("Pending Offboarding Officer", "Offboarding Officer"), ("Pending Finance Manager", "Finance Manager")):
			self.assertEqual(run("Assign Subcontractor Exit Step", self.doc(state)), {"assigned_user": "", "assigned_role": role})


class TestFillSubcontractorExitDefaults(FrappeTestCase):
	def test_fills_requester_and_default_manager(self):
		doc = frappe._dict(name="SE-TEST", owner="owner@example.com", requested_by=None, operations_manager_user=None)
		with patch("frappe.db.get_single_value", return_value="om@example.com"), patch("frappe.db.set_value") as set_value:
			result = run("Fill Subcontractor Exit Defaults", doc)
		values = {"requested_by": "owner@example.com", "operations_manager_user": "om@example.com"}
		set_value.assert_called_once_with("Subcontractor Exit", "SE-TEST", values, update_modified=False)
		self.assertEqual(result, values)

	def test_keeps_values_already_set(self):
		doc = frappe._dict(name="SE-TEST", owner="o@example.com", requested_by="r@example.com", operations_manager_user="m@example.com")
		with patch("frappe.db.set_value") as set_value:
			self.assertEqual(run("Fill Subcontractor Exit Defaults", doc), {})
		set_value.assert_not_called()


class TestSubcontractorExitController(FrappeTestCase):
	def test_penalty_needs_remarks(self):
		doc = frappe.new_doc("Subcontractor Exit")
		doc.append("subcontract_exit_employee", {"employee_id": "HR-EMP-X", "penalize_the_employee": 1})
		self.assertRaises(frappe.ValidationError, doc.validate_penalty_remarks)
		doc.subcontract_exit_employee[0].supervisor_remarks = "Late"
		doc.validate_penalty_remarks()

	def test_fetch_needs_both_filters(self):
		from one_fm.one_fm.doctype.subcontractor_exit.subcontractor_exit import fetch_subcontractor_employees
		self.assertRaises(frappe.ValidationError, fetch_subcontractor_employees, "", "Site")

	def test_fetch_filters_active_subcontractor_staff(self):
		from one_fm.one_fm.doctype.subcontractor_exit.subcontractor_exit import fetch_subcontractor_employees
		with patch("frappe.get_list", return_value=[]) as get_list:
			fetch_subcontractor_employees("Sub", "Site")
		self.assertEqual(get_list.call_args.kwargs["filters"], {"status": "Active", "employment_type": "Subcontractor", "custom_subcontractor_name": "Sub", "site": "Site"})
