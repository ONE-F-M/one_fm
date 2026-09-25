# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002496: the renamed PACI states, the PRO's own update states, and the two rules.

Read off the fixtures rather than the live Workflow: the configuration reaches a site on
migrate, and this has to hold on the branch before anybody has run one.
"""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.custom.assignment_rule.assignment_rule import get_assignment_rule_json_file
from one_fm.custom.workflow.workflow import get_workflow_json_file
from one_fm.grd.doctype.paci.paci import PENDING_GR_OPERATOR, PENDING_PRO

GRO = "Government Relations Operator"
ADDRESS_BY_PRO = "Pending Address Update by PRO"
PHOTO_BY_PRO = "Pending Photo Update by PRO"
RETIRED_STATES = ("Pending GR Operator", "Pending PRO")


class TestPACIStateNames(FrappeTestCase):
	def setUp(self):
		self.workflow = get_workflow_json_file("paci.json")
		self.states = {state["state"]: state for state in self.workflow["states"]}
		self.transitions = {
			(t["state"], t["action"], t["next_state"]): t for t in self.workflow["transitions"]
		}

	def test_the_old_state_names_are_gone(self):
		for state in RETIRED_STATES:
			self.assertNotIn(state, self.states)

	def test_the_controller_constants_match_the_workflow(self):
		"""paci.py writes these states directly, so a drift here assigns nothing."""
		self.assertIn(PENDING_PRO, self.states)
		self.assertIn(PENDING_GR_OPERATOR, self.states)

	def test_no_transition_points_at_a_state_that_is_gone(self):
		for state, _action, next_state in self.transitions:
			self.assertIn(state, self.states)
			self.assertIn(next_state, self.states)


class TestTheProUpdateStates(FrappeTestCase):
	def setUp(self):
		self.workflow = get_workflow_json_file("paci.json")
		self.states = {state["state"]: state for state in self.workflow["states"]}
		self.transitions = {
			(t["state"], t["action"], t["next_state"]): t for t in self.workflow["transitions"]
		}

	def test_the_pro_has_update_states_of_their_own(self):
		"""An address or photo PACI rejects can be the PRO's to fix - they hold the portal."""
		for state in (ADDRESS_BY_PRO, PHOTO_BY_PRO):
			self.assertIn(state, self.states)
			self.assertEqual(self.states[state]["allow_edit"], "PRO")
			self.assertEqual(self.states[state]["doc_status"], "0")

	def test_the_new_states_carry_a_style(self):
		"""create_workflow_state() inserts the Workflow State master with the fixture's
		`style`, which is mandatory on that DocType. Without one the state is never
		created and the workflow save fails on a link to it - both silently."""
		for state in (ADDRESS_BY_PRO, PHOTO_BY_PRO, PENDING_GR_OPERATOR):
			self.assertTrue(self.states[state].get("style"), state)

	def test_each_pro_state_looks_like_the_operator_state_it_mirrors(self):
		for pro_state, operator_state in (
			(ADDRESS_BY_PRO, "Pending Address Update"),
			(PHOTO_BY_PRO, "Pending Photo Update"),
		):
			self.assertEqual(
				self.states[pro_state]["style"], self.states[operator_state]["style"], pro_state
			)

	def test_the_operator_sends_the_work_and_the_pro_sends_it_back(self):
		out = {
			(PENDING_GR_OPERATOR, "Update Address By PRO", ADDRESS_BY_PRO): GRO,
			(PENDING_GR_OPERATOR, "Update Photo by PRO", PHOTO_BY_PRO): GRO,
			(ADDRESS_BY_PRO, "Address Updated", PENDING_GR_OPERATOR): "PRO",
			(PHOTO_BY_PRO, "Photo Updated", PENDING_GR_OPERATOR): "PRO",
		}
		for key, role in out.items():
			self.assertIn(key, self.transitions, key)
			self.assertEqual(self.transitions[key]["allowed"], role, key)

	def test_the_operators_own_update_states_are_untouched(self):
		"""The operator still fixes what is theirs to fix."""
		for state in ("Pending Address Update", "Pending Photo Update"):
			self.assertEqual(self.states[state]["allow_edit"], GRO)

	def test_the_route_to_the_pro_is_the_operators_to_take(self):
		"""It was "Save" allowed to PRO, which no PRO can reach - a Draft is the operator's."""
		key = ("Draft", "Submit to PRO", PENDING_PRO)
		self.assertIn(key, self.transitions)
		self.assertEqual(self.transitions[key]["allowed"], GRO)
		self.assertEqual(
			self.transitions[key]["condition"], 'doc.category == "New Application"'
		)


class TestTheProUserField(FrappeTestCase):
	def setUp(self):
		self.field = next(
			field
			for field in json.loads(
				frappe.read_file(
					frappe.get_app_path("one_fm", "grd", "doctype", "paci", "paci.json")
				)
			)["fields"]
			if field["fieldname"] == "pro_user"
		)

	def test_it_offers_only_users_who_hold_the_pro_role(self):
		self.assertEqual(
			json.loads(self.field["link_filters"]), [["User", "role", "=", "PRO"]]
		)

	def test_it_is_mandatory_in_every_state_the_pro_holds(self):
		"""A state only the PRO can leave, with no PRO named on it, is a stuck record."""
		for state in (PENDING_PRO, ADDRESS_BY_PRO, PHOTO_BY_PRO):
			self.assertIn(state, self.field["mandatory_depends_on"])


class TestTheAssignmentRulesFollowTheRename(FrappeTestCase):
	def test_the_operator_rule_names_the_renamed_state(self):
		rule = get_assignment_rule_json_file("action_paci.json")
		self.assertIn(PENDING_GR_OPERATOR, rule["assign_condition"])
		for field in ("assign_condition", "unassign_condition", "close_condition"):
			for retired in RETIRED_STATES:
				self.assertNotIn(retired, rule[field] or "", f"{field} / {retired}")

	def test_the_pro_rule_covers_all_three_states_the_pro_holds(self):
		rule = get_assignment_rule_json_file("paci_pro.json")
		self.assertEqual(rule["field"], "pro_user")
		for state in (PENDING_PRO, ADDRESS_BY_PRO, PHOTO_BY_PRO):
			self.assertIn(state, rule["assign_condition"])
			self.assertIn(state, rule["unassign_condition"])

	def test_the_patch_is_registered(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		self.assertIn("one_fm.patches.v15_0.update_paci_workflow_and_rules", patches)
