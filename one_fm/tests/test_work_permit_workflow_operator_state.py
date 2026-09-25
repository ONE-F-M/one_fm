# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002497: the Work Permit belongs to the GR Operator from the moment it is saved.

Read off the fixtures rather than the live Workflow: the configuration reaches a site on
migrate, and this has to hold on the branch before anybody has run one.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.custom.assignment_rule.assignment_rule import get_assignment_rule_json_file
from one_fm.custom.workflow.workflow import get_workflow_json_file

PENDING_GRO = "Pending by GR Operator"
RETIRED_STATE = "Pending By Operator"
BYPASSED_STATE = "Apply Online by PRO"
GRO = "Government Relations Operator"


class TestTheOperatorState(FrappeTestCase):
	def setUp(self):
		self.workflow = get_workflow_json_file("work_permit.json")
		self.states = {state["state"]: state for state in self.workflow["states"]}
		self.transitions = {
			(t["state"], t["action"], t["next_state"]): t for t in self.workflow["transitions"]
		}

	def test_the_two_spellings_are_one_state(self):
		self.assertIn(PENDING_GRO, self.states)
		self.assertNotIn(RETIRED_STATE, self.states)
		self.assertEqual(self.states[PENDING_GRO]["allow_edit"], GRO)

	def test_every_state_carries_a_style(self):
		"""create_workflow_state() inserts the Workflow State master with the fixture's
		`style`, which is mandatory on that DocType. "Pending by GR Operator" has no
		master yet, so without one it is never created and the workflow save fails on a
		link to it - both silently, because the helpers log instead of raising."""
		for name, state in self.states.items():
			self.assertTrue(state.get("style"), name)

	def test_the_renamed_operator_state_keeps_its_colour(self):
		self.assertEqual(self.states[PENDING_GRO]["style"], "Warning")

	def test_a_draft_saves_straight_to_the_operator(self):
		self.assertIn(("Draft", "Save", PENDING_GRO), self.transitions)

	def test_apply_hangs_off_the_operator_state(self):
		"""It hung off a PRO state whose only assignment rule has been disabled since
		WI-002182, so the permit passed through a step with no owner."""
		self.assertIn((PENDING_GRO, "Apply", "Pending GR Manager"), self.transitions)

	def test_payment_comes_back_to_the_operator_and_the_operator_completes(self):
		self.assertIn(("Pending  For Payment", "Paid", PENDING_GRO), self.transitions)
		self.assertIn((PENDING_GRO, "Done", "Completed"), self.transitions)

	def test_nothing_routes_into_the_bypassed_state_any_more(self):
		for _state, _action, next_state in self.transitions:
			self.assertNotEqual(next_state, BYPASSED_STATE)

	def test_the_bypassed_state_is_kept_but_inert(self):
		"""The disabled Work Permit-PRO rule still names it - it is what that rule would
		come back to if the PRO step is ever turned on."""
		self.assertIn(BYPASSED_STATE, self.states)
		for state, _action, _next_state in self.transitions:
			self.assertNotEqual(state, BYPASSED_STATE)

	def test_no_state_claims_to_write_a_field_it_does_not_name(self):
		"""update_value without update_field writes nothing - five states carried one."""
		for name, state in self.states.items():
			if not state.get("update_field"):
				self.assertIn(state.get("update_value") or "", ("", "Rejected"), name)

	def test_no_transition_points_at_a_state_that_is_gone(self):
		for state, _action, next_state in self.transitions:
			self.assertIn(state, self.states)
			self.assertIn(next_state, self.states)


class TestTheOperatorRuleFollows(FrappeTestCase):
	def setUp(self):
		self.rule = get_assignment_rule_json_file("work_permit_gr_operator.json")

	def test_it_assigns_at_the_operator_state(self):
		self.assertIn(PENDING_GRO, self.rule["assign_condition"])
		self.assertIn(PENDING_GRO, self.rule["unassign_condition"])

	def test_it_no_longer_names_states_the_permit_does_not_reach(self):
		for field in ("assign_condition", "unassign_condition", "close_condition"):
			self.assertNotIn(RETIRED_STATE, self.rule[field] or "", field)
			self.assertNotIn(BYPASSED_STATE, self.rule[field] or "", field)


class TestTheRestartPath(FrappeTestCase):
	def test_a_restarted_application_lands_where_apply_lives(self):
		"""set_restart_application wrote the bypassed state, which now has no action."""
		source = frappe.read_file(frappe.get_app_path("one_fm", "hiring", "utils.py"))
		self.assertIn(f"wp.workflow_state = '{PENDING_GRO}'", source)
		self.assertNotIn(f"wp.workflow_state = '{BYPASSED_STATE}'", source)

	def test_the_patch_is_registered(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		self.assertIn("one_fm.patches.v15_0.update_work_permit_workflow_and_rules", patches)
