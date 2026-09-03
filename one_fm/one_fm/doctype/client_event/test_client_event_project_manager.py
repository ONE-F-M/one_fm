# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002184: a Client Event is approved by the manager of the project it is for.

The Operations Manager approved everything, whatever project the event belonged to. The
project's own manager approves it now - and an event with no project keeps the old route,
because there is no project manager for it to go to.
"""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.client_event.client_event import PENDING_STATES

WORKFLOW_FILE = ("one_fm", "custom", "workflow", "client_event.json")
PM_STATE = "Pending Project Manager"
OM_STATE = "Pending Operations Manager"


def _workflow():
	return json.loads(frappe.read_file(frappe.get_app_path(*WORKFLOW_FILE)))


def _submit_routes():
	return {
		(t["state"], t["next_state"]): t
		for t in _workflow()["transitions"] if t["action"] == "Submit for Review"
	}


class TestTheProjectManagerReachesTheEvent(FrappeTestCase):
	"""The assignment rule reads a field. If nothing fills it, it assigns nobody."""

	def test_the_project_names_its_manager_on_the_event(self):
		field = frappe.get_meta("Client Event").get_field("project_manager")

		self.assertEqual(field.options, "Employee")
		self.assertEqual(field.fetch_from, "project.project_manager")

	def test_the_manager_names_their_user(self):
		field = frappe.get_meta("Client Event").get_field("project_manager_user")

		self.assertEqual(field.options, "User")
		self.assertEqual(field.fetch_from, "project_manager.user_id")

	def test_the_chain_it_fetches_through_exists(self):
		"""project.project_manager is a custom field; a rename there breaks this silently."""
		self.assertTrue(frappe.get_meta("Project").get_field("project_manager"))
		self.assertEqual(frappe.get_meta("Project").get_field("project_manager").options, "Employee")

	def test_the_operations_manager_is_asked_for_only_without_one(self):
		field = frappe.get_meta("Client Event").get_field("operations_manager")

		self.assertEqual(field.depends_on, "eval:!doc.project_manager_user")


class TestTheProjectDecidesTheRoute(FrappeTestCase):
	def test_an_event_with_a_project_goes_to_its_manager(self):
		route = _submit_routes().get(("Draft", PM_STATE))

		self.assertIsNotNone(route, f"Draft does not reach {PM_STATE}")
		self.assertEqual(route["condition"], "doc.project")
		self.assertEqual(route["allowed"], "Operations Supervisor")

	def test_an_event_without_one_keeps_the_old_route(self):
		route = _submit_routes().get(("Draft", OM_STATE))

		self.assertIsNotNone(route, "an event with no project has no route out of Draft")
		self.assertEqual(route["condition"], "not doc.project")

	def test_the_supervisor_can_submit_either_way(self):
		"""The BA export allowed only the Operations Manager to submit the no-project path,
		which left a supervisor unable to submit their own project-less event."""
		for route in _submit_routes().values():
			with self.subTest(next_state=route["next_state"]):
				self.assertEqual(route["allowed"], "Operations Supervisor")

	def test_both_routes_are_conditional(self):
		"""An unconditional transition beside a conditional one is taken regardless of the
		condition - every event would follow whichever the workflow lists first."""
		for route in _submit_routes().values():
			with self.subTest(next_state=route["next_state"]):
				self.assertTrue(route.get("condition"))

	def test_the_conditions_actually_evaluate(self):
		"""Workflow conditions get `doc`, and one that raises is a hard error on form load."""
		for has_project in (True, False):
			doc = frappe._dict({"project": "PROJ-01" if has_project else None})
			expected = (Draft_PM := bool(has_project))
			for (state, nxt), route in _submit_routes().items():
				with self.subTest(project=has_project, next_state=nxt):
					result = bool(frappe.safe_eval(route["condition"], None, {"doc": doc}))
					self.assertEqual(result, expected if nxt == PM_STATE else not expected)


class TestWhoMayActOnIt(FrappeTestCase):
	def setUp(self):
		self.workflow = _workflow()

	def _transitions(self, state):
		return [t for t in self.workflow["transitions"] if t["state"] == state]

	def test_only_the_project_manager_approves_or_rejects(self):
		for t in self._transitions(PM_STATE):
			if t["action"] in ("Approve", "Reject"):
				with self.subTest(action=t["action"]):
					self.assertEqual(t["allowed"], "Project Manager")

	def test_the_supervisor_may_recall_their_submission(self):
		recalls = {
			t["allowed"] for t in self._transitions(PM_STATE) if t["action"] == "Return To Draft"
		}

		self.assertEqual(recalls, {"Project Manager", "Operations Supervisor"})

	def test_both_roles_may_edit_an_approved_event(self):
		editors = {
			s["allow_edit"] for s in self.workflow["states"] if s["state"] == "Approved"
		}

		self.assertEqual(editors, {"Project Manager", "Operations Supervisor"})

	def test_only_a_manager_cancels(self):
		cancels = {
			t["allowed"] for t in self.workflow["transitions"] if t["action"] == "Cancel"
		}

		self.assertNotIn("Operations Supervisor", cancels)
		self.assertIn("Project Manager", cancels)

	def test_every_state_carries_a_style(self):
		"""Workflow State.style is mandatory here: a state without one fails to be created,
		the workflow save then fails on a missing state, and create_workflow logs it instead
		of raising."""
		for s in self.workflow["states"]:
			with self.subTest(state=s["state"]):
				self.assertTrue(s.get("style"))


class TestTheApproverFallback(FrappeTestCase):
	"""The last acceptance criterion: no project and no project manager means the site's
	default Operations Manager, written onto the document so the rule can read it."""

	def _event(self, **fields):
		doc = frappe.new_doc("Client Event")
		doc.update(fields)
		return doc

	def test_it_names_the_site_default_when_nobody_else_is_named(self):
		default = frappe.db.get_single_value("Operation Settings", "default_operation_manager")
		if not default:
			self.skipTest("Operation Settings names no default Operation Manager")

		doc = self._event()
		doc.set_approver()

		self.assertEqual(doc.operations_manager, default)

	def test_a_project_manager_leaves_it_alone(self):
		doc = self._event(project_manager_user="Administrator")
		doc.set_approver()

		self.assertFalse(doc.operations_manager)

	def test_one_named_by_hand_is_not_overwritten(self):
		doc = self._event(operations_manager="Administrator")
		doc.set_approver()

		self.assertEqual(doc.operations_manager, "Administrator")


class TestBothPendingStatesAreRecognised(FrappeTestCase):
	def test_the_controller_knows_both(self):
		"""validate_date_time skips every state but the pending ones. Left naming only the
		old one, an event waiting on its project manager would lose its date checks."""
		self.assertEqual(set(PENDING_STATES), {PM_STATE, OM_STATE})


class TestTheAssignmentRules(FrappeTestCase):
	def _rule(self, filename):
		return json.loads(frappe.read_file(frappe.get_app_path(
			"one_fm", "custom", "assignment_rule", filename)))

	def test_the_project_manager_rule_assigns_their_user(self):
		rule = self._rule("assigning_project_manager_for_approval_client_event.json")

		self.assertEqual(rule["name"], "Client Event - Pending Project Manager")
		self.assertEqual(rule["rule"], "Based on Field")
		self.assertEqual(rule["field"], "project_manager_user")
		self.assertIn(PM_STATE, rule["assign_condition"])

	def test_the_draft_rule_releases_the_owner_at_the_new_state(self):
		rule = self._rule("returning_to_operations_supervisor_of_client_event.json")

		self.assertEqual(rule["unassign_condition"], f'workflow_state == "{PM_STATE}"')

	def test_no_rule_carries_a_blank_process_task(self):
		"""An empty custom_routine_task is written straight through and blanks the link."""
		for filename in (
			"assigning_project_manager_for_approval_client_event.json",
			"assigning_operations_manager_for_approval_client_event.json",
			"returning_to_operations_supervisor_of_client_event.json",
		):
			with self.subTest(filename=filename):
				self.assertNotIn("custom_routine_task", self._rule(filename))

	def test_every_condition_runs_on_every_state(self):
		"""assign_condition is safe_eval'd with the document's own dict as locals; anything
		that raises is swallowed into a msgprint and the rule silently assigns nobody."""
		states = {s["state"] for s in _workflow()["states"]}
		for filename in (
			"assigning_project_manager_for_approval_client_event.json",
			"assigning_operations_manager_for_approval_client_event.json",
			"returning_to_operations_supervisor_of_client_event.json",
		):
			rule = self._rule(filename)
			for key in ("assign_condition", "unassign_condition", "close_condition"):
				if not rule.get(key):
					continue
				for state in states:
					with self.subTest(filename=filename, key=key, state=state):
						frappe.safe_eval(rule[key], None, {"workflow_state": state})
