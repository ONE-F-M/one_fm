# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002186: an OJT request is approved by the manager of the trainee's project.

The Operations Manager approved every request. The project's own manager approves them
now, reached by the same fetch chain Client Event uses (WI-002184).
"""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

WORKFLOW_FILE = ("one_fm", "custom", "workflow", "on_the_job_training.json")
RULE_DIR = ("one_fm", "custom", "assignment_rule")

PM = "Project Manager"
OM = "Operations Manager"
APPROVAL_STATES = ("Pending Approval", "Pending Extension Approval")


def _workflow():
	return json.loads(frappe.read_file(frappe.get_app_path(*WORKFLOW_FILE)))


def _rule(filename):
	return json.loads(frappe.read_file(frappe.get_app_path(*RULE_DIR, filename)))


class TestTheManagerReachesTheRequest(FrappeTestCase):
	"""The BA export left the Employee link with no fetch_from, which would have left the
	whole chain empty and the assignment rule assigning nobody - silently."""

	def test_the_project_names_its_manager_on_the_request(self):
		field = frappe.get_meta("On the Job Training").get_field("project_manager_employee")

		self.assertEqual(field.options, "Employee")
		self.assertEqual(field.fetch_from, "project.project_manager")

	def test_the_manager_names_their_user(self):
		field = frappe.get_meta("On the Job Training").get_field("project_manager")

		self.assertEqual(field.options, "User")
		self.assertEqual(field.fetch_from, "project_manager_employee.user_id")

	def test_the_project_still_comes_from_the_shift(self):
		"""The first link in the chain: Operations Role -> Shift -> Project -> Manager."""
		meta = frappe.get_meta("On the Job Training")

		self.assertEqual(meta.get_field("project").fetch_from, "operations_shift.project")
		self.assertEqual(meta.get_field("operations_shift").fetch_from, "operations_role.shift")

	def test_the_chain_it_fetches_through_exists(self):
		field = frappe.get_meta("Project").get_field("project_manager")

		self.assertIsNotNone(field, "Project.project_manager is a custom field; it is gone")
		self.assertEqual(field.options, "Employee")

	def test_the_project_manager_is_shown_only_with_a_project(self):
		field = frappe.get_meta("On the Job Training").get_field("project_manager")

		self.assertEqual(field.depends_on, "eval:doc.project")

	def test_the_operations_manager_is_off_the_form(self):
		"""Kept for the records that already name one, but not asked for any more."""
		self.assertTrue(frappe.get_meta("On the Job Training").get_field("operations_manager").hidden)


class TestTheProjectManagerApproves(FrappeTestCase):
	def setUp(self):
		self.workflow = _workflow()

	def test_no_approval_is_left_with_the_operations_manager(self):
		approvers = {
			t["allowed"] for t in self.workflow["transitions"] if t["state"] in APPROVAL_STATES
		}

		self.assertNotIn(OM, approvers)
		self.assertEqual(approvers, {PM})

	def test_the_supervisor_still_submits(self):
		submits = [
			t for t in self.workflow["transitions"]
			if t["state"] == "Draft" and t["action"] == "Submit for Review"
		]

		self.assertEqual([t["allowed"] for t in submits], ["Operations Supervisor"])

	def test_the_manager_holds_every_state_they_approve_from(self):
		editors = {
			s["state"]: s["allow_edit"] for s in self.workflow["states"]
			if s["state"] in ("Pending Approval", "Rejected", "OJT Extension Approved")
		}

		self.assertEqual(set(editors.values()), {PM})

	def test_the_supervisor_may_still_edit_an_approved_request(self):
		editors = {s["allow_edit"] for s in self.workflow["states"] if s["state"] == "Approved"}

		self.assertEqual(editors, {PM, "Operations Supervisor"})

	def test_no_operations_manager_is_left_anywhere_in_the_workflow(self):
		roles = {s.get("allow_edit") for s in self.workflow["states"]}
		roles |= {t.get("allowed") for t in self.workflow["transitions"]}

		self.assertNotIn(OM, roles)

	def test_every_state_carries_a_style(self):
		"""Workflow State.style is mandatory here; a state without one is never created and
		create_workflow logs the failure instead of raising."""
		for s in self.workflow["states"]:
			with self.subTest(state=s["state"]):
				self.assertTrue(s.get("style"))

	def test_the_extension_conditions_still_evaluate(self):
		"""A condition that raises is a hard error on form load, not a skipped transition."""
		for t in self.workflow["transitions"]:
			if not t.get("condition"):
				continue
			for extended in (0, 1):
				with self.subTest(action=t["action"], date_extended=extended):
					frappe.safe_eval(
						t["condition"], None, {"doc": frappe._dict({"date_extended": extended})}
					)


class TestTheAssignmentRules(FrappeTestCase):
	def test_the_approval_rule_assigns_the_project_manager(self):
		rule = _rule("assigning_project_manager_for_approval.json")

		self.assertEqual(rule["name"], "Assigning Project Manager for Approval")
		self.assertEqual(rule["rule"], "Based on Field")
		self.assertEqual(rule["field"], "project_manager")
		self.assertEqual(rule["document_type"], "On the Job Training")

	def test_the_old_rule_file_is_gone(self):
		"""Left behind, it would assign the Operations Manager at the same state the new
		rule assigns the Project Manager - two rules, one queue, split in half."""
		import os

		self.assertFalse(os.path.exists(frappe.get_app_path(
			*RULE_DIR, "assigning_operations_manager_for_approval.json")))

	def test_the_supervisor_rule_is_untouched(self):
		rule = _rule("returning_to_operations_supervisor_of_ojt_request.json")

		self.assertEqual(rule["field"], "operations_supervisor")
		self.assertEqual(rule["assign_condition"], 'workflow_state == "Draft"')

	def test_no_rule_carries_a_blank_process_task(self):
		for filename in (
			"assigning_project_manager_for_approval.json",
			"returning_to_operations_supervisor_of_ojt_request.json",
		):
			with self.subTest(filename=filename):
				self.assertNotIn("custom_routine_task", _rule(filename))

	def test_every_condition_runs_on_every_state(self):
		states = {s["state"] for s in _workflow()["states"]}
		for filename in (
			"assigning_project_manager_for_approval.json",
			"returning_to_operations_supervisor_of_ojt_request.json",
		):
			rule = _rule(filename)
			for key in ("assign_condition", "unassign_condition", "close_condition"):
				if not rule.get(key):
					continue
				for state in states:
					with self.subTest(filename=filename, key=key, state=state):
						frappe.safe_eval(rule[key], None, {"workflow_state": state})

	def test_every_state_a_condition_names_is_one_the_workflow_has(self):
		"""What catches the next rename before it silently assigns nobody."""
		import re

		states = {s["state"] for s in _workflow()["states"]}
		for filename in (
			"assigning_project_manager_for_approval.json",
			"returning_to_operations_supervisor_of_ojt_request.json",
		):
			rule = _rule(filename)
			for key in ("assign_condition", "unassign_condition", "close_condition"):
				for quoted in re.findall(r'"([^"]+)"', rule.get(key) or ""):
					with self.subTest(filename=filename, state=quoted):
						self.assertIn(quoted, states)
