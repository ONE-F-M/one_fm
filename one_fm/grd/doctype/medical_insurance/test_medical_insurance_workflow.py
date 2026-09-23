# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002494: the Medical Insurance workflow and the rule that puts it on a desk."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.custom.assignment_rule.assignment_rule import get_assignment_rule_json_file
from one_fm.custom.workflow.workflow import get_workflow_json_file

DOCTYPE = "Medical Insurance"
OLD_STATE = "Apply Online by PRO"
NEW_STATE = "Apply Online by GR Operator"
RULE_NAME = "Medical Insurance - GRO"

EXPECTED_STATUS = {
	"Draft": "Draft",
	NEW_STATE: "Draft",
	"Completed": "Submitted",
	"Cancelled": "Canceled",
}

EXPECTED_TRANSITIONS = (
	("Draft", "Submit", NEW_STATE),
	(NEW_STATE, "Done", "Completed"),
)


class TestMedicalInsuranceWorkflow(FrappeTestCase):
	def setUp(self):
		self.workflow = get_workflow_json_file("medical_insurance.json")

	def test_the_submitted_state_names_the_gr_operator(self):
		"""No PRO touches Medical Insurance - the GR Operator applies online themselves."""
		states = [state["state"] for state in self.workflow["states"]]
		self.assertIn(NEW_STATE, states)
		self.assertNotIn(OLD_STATE, states)

	def test_every_state_writes_status(self):
		"""The Data field beside the workflow has to say what the workflow says."""
		written = {
			state["state"]: (state.get("update_field"), state.get("update_value"))
			for state in self.workflow["states"]
		}
		for state, status in EXPECTED_STATUS.items():
			self.assertEqual(written.get(state), ("status", status))

	def test_the_status_values_are_options_the_field_offers(self):
		"""A value outside the Select is written and then fails the document's own validation."""
		options = frappe.get_meta(DOCTYPE).get_field("status").options.split("\n")
		for status in EXPECTED_STATUS.values():
			self.assertIn(status, options)

	def test_the_transitions_are_the_two_the_story_asks_for(self):
		transitions = {
			(t["state"], t["action"], t["next_state"]) for t in self.workflow["transitions"]
		}
		self.assertEqual(transitions, set(EXPECTED_TRANSITIONS))

	def test_no_transition_points_at_a_state_that_is_gone(self):
		"""A transition naming the old state is one an operator can never take."""
		states = {state["state"] for state in self.workflow["states"]}
		for transition in self.workflow["transitions"]:
			self.assertIn(transition["state"], states)
			self.assertIn(transition["next_state"], states)

	def test_the_assignment_rule_covers_the_states_somebody_is_still_working(self):
		rule = get_assignment_rule_json_file("medical_insurance_gro.json")
		self.assertEqual(rule["name"], RULE_NAME)
		self.assertEqual(rule["document_type"], DOCTYPE)
		self.assertEqual(rule["rule"], "Based on Field")
		self.assertEqual(rule["field"], "owner")
		self.assertEqual(rule["disabled"], 0)
		self.assertIn(NEW_STATE, rule["assign_condition"])
		self.assertIn("Draft", rule["assign_condition"])
		self.assertIn(NEW_STATE, rule["close_condition"])

	def test_the_assignment_rule_carries_its_days(self):
		"""An Assignment Rule Day row exported with another site's name is silently dropped."""
		rule = get_assignment_rule_json_file("medical_insurance_gro.json")
		self.assertEqual(len(rule["assignment_days"]), 7)
		for row in rule["assignment_days"]:
			self.assertNotIn("name", row)

	def test_the_rule_is_provisioned_on_install(self):
		source = frappe.read_file(
			frappe.get_app_path("one_fm", "setup", "assignment_rule.py")
		)
		self.assertIn("medical_insurance_gro.json", source)

	def test_the_patch_is_registered(self):
		patches = frappe.read_file(frappe.get_app_path("one_fm", "patches.txt"))
		self.assertIn(
			"one_fm.patches.v15_0.update_medical_insurance_workflow_and_rule", patches
		)
