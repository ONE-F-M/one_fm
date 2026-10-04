# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002495: the Residency (MOI) workflow, the PRO field, and the two rules that assign it."""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.custom.assignment_rule.assignment_rule import get_assignment_rule_json_file
from one_fm.custom.workflow.workflow import get_workflow_json_file

DOCTYPE = "Residency"
OLD_STATE = "Apply Online by PRO"
PENDING_PRO = "Pending by PRO"
PENDING_GRO = "Pending by GR Operator"

EXPECTED_TRANSITIONS = {
	("Draft", "Assign PRO", PENDING_PRO),
	("Draft", "Process Online", PENDING_GRO),
	(PENDING_PRO, "Submit to GR Operator", PENDING_GRO),
	(PENDING_GRO, "Done", "Completed"),
}


class TestResidencyWorkflow(FrappeTestCase):
	def setUp(self):
		self.workflow = get_workflow_json_file("moi.json")
		self.states = {state["state"]: state for state in self.workflow["states"]}

	def test_the_single_state_flow_is_gone(self):
		"""One state was standing in for the draft, the PRO's turn and the operator's."""
		self.assertNotIn(OLD_STATE, self.states)
		for state in ("Draft", PENDING_PRO, PENDING_GRO, "Completed", "Cancelled"):
			self.assertIn(state, self.states)

	def test_the_pro_state_is_the_pros_to_edit(self):
		self.assertEqual(self.states[PENDING_PRO]["allow_edit"], "PRO")

	def test_only_completed_submits_the_document(self):
		for name, state in self.states.items():
			expected = "1" if name == "Completed" else "0"
			self.assertEqual(state["doc_status"], expected, name)

	def test_every_state_carries_a_style(self):
		"""create_workflow_state() inserts the Workflow State master with the fixture's
		`style`, which is mandatory on that DocType. A state without one is never created,
		and the workflow save then fails on a link to a state that does not exist - both
		silently, because the helpers log instead of raising."""
		for state in self.workflow["states"]:
			self.assertTrue(state.get("style"), state["state"])

	def test_the_new_operator_state_looks_like_the_one_it_replaces(self):
		self.assertEqual(self.states[PENDING_GRO]["style"], "Warning")

	def test_the_transitions_are_the_four_the_story_asks_for(self):
		transitions = {
			(t["state"], t["action"], t["next_state"]) for t in self.workflow["transitions"]
		}
		self.assertEqual(transitions, EXPECTED_TRANSITIONS)

	def test_the_pro_hands_the_record_back_and_the_operator_finishes_it(self):
		"""Only the PRO may leave the PRO state; only the operator may complete."""
		by_key = {
			(t["state"], t["action"]): t["allowed"] for t in self.workflow["transitions"]
		}
		self.assertEqual(by_key[(PENDING_PRO, "Submit to GR Operator")], "PRO")
		self.assertEqual(
			by_key[(PENDING_GRO, "Done")], "Government Relations Operator"
		)

	def test_no_transition_points_at_a_state_that_is_gone(self):
		for transition in self.workflow["transitions"]:
			self.assertIn(transition["state"], self.states)
			self.assertIn(transition["next_state"], self.states)

	def test_residency_carries_a_pro_user_field_filtered_to_pros(self):
		"""A Based on Field rule pointed at a missing field assigns nobody, silently.

		Read off the DocType JSON rather than the live meta: the field reaches a site on
		migrate, and this has to hold on the branch before anybody has run one.
		"""
		definition = json.loads(
			frappe.read_file(
				frappe.get_app_path("one_fm", "grd", "doctype", "residency", "residency.json")
			)
		)
		field = next(f for f in definition["fields"] if f["fieldname"] == "pro_user")
		self.assertEqual(field["fieldtype"], "Link")
		self.assertEqual(field["options"], "User")
		self.assertEqual(json.loads(field["link_filters"]), [["User", "role", "=", "PRO"]])
		self.assertIn("pro_user", definition["field_order"])

	def test_the_operator_rule_covers_the_states_the_operator_holds(self):
		rule = get_assignment_rule_json_file("residency_gr_operator.json")
		self.assertEqual(rule["name"], "Residency - GR Operator")
		self.assertEqual(rule["field"], "owner")
		self.assertEqual(rule["disabled"], 0)
		self.assertIn("Draft", rule["assign_condition"])
		self.assertIn(PENDING_GRO, rule["assign_condition"])

	def test_the_pro_rule_assigns_on_a_state_the_workflow_actually_has(self):
		"""The BA site's copy names a state its own workflow dropped, so it never fires."""
		rule = get_assignment_rule_json_file("residency_pro.json")
		self.assertEqual(rule["name"], "Residency - PRO")
		self.assertEqual(rule["field"], "pro_user")
		self.assertIn(PENDING_PRO, rule["assign_condition"])
		self.assertNotIn(OLD_STATE, rule["assign_condition"])

	def test_neither_rule_closes_the_other_one_s_assignment(self):
		"""Frappe closes ToDos by document, not by rule.

		`apply_assignment_rule` collects the ToDos to close with

		    frappe.get_all("ToDo", filters={"reference_type": ..., "reference_name": ...})

		with no filter on which rule made them - so a close_condition that is merely "not
		my states" closes EVERY assignment on the record. With two rules on Residency, the
		operator's rule fired the moment the record reached Pending by PRO and closed the
		PRO's brand-new ToDo, and the PRO's rule did the same to the operator's. The
		handover produced a closed assignment and the record reached nobody's desk.

		`unassign_condition` is the right tool: `apply_unassign` is scoped to the rule's
		own assignments. Both rules rely on it and neither closes.
		"""
		for filename in ("residency_gr_operator.json", "residency_pro.json"):
			rule = get_assignment_rule_json_file(filename)
			self.assertFalse(rule["close_condition"], filename)
			self.assertTrue(rule["unassign_condition"], filename)

	def test_each_rule_releases_the_record_when_it_leaves_its_own_states(self):
		operator = get_assignment_rule_json_file("residency_gr_operator.json")
		self.assertEqual(
			operator["unassign_condition"],
			'workflow_state not in ["Draft", "Pending by GR Operator"]',
		)

		pro = get_assignment_rule_json_file("residency_pro.json")
		self.assertEqual(pro["unassign_condition"], 'workflow_state != "Pending by PRO"')

	def test_both_rules_carry_their_days(self):
		"""An Assignment Rule Day row exported with another site's name is silently dropped."""
		for filename in ("residency_gr_operator.json", "residency_pro.json"):
			rule = get_assignment_rule_json_file(filename)
			self.assertEqual(len(rule["assignment_days"]), 7, filename)
			for row in rule["assignment_days"]:
				self.assertNotIn("name", row)

	def test_the_rules_are_provisioned_on_install(self):
		source = frappe.read_file(frappe.get_app_path("one_fm", "setup", "assignment_rule.py"))
		self.assertIn("residency_gr_operator.json", source)
		self.assertIn("residency_pro.json", source)

	def test_the_patch_is_registered(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		self.assertIn("one_fm.patches.v15_0.update_residency_workflow_and_rules", patches)
