# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""The Medical Appointment workflow, as the business analyst's site defines it."""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

WORKFLOW = "Medical Appointment"
DRAFT = "Draft"
DRAFT_TRANSITION = (DRAFT, "Submit to Supervisor", "Pending Supervisor")

# State to style, in the order the analyst's site lists them. The order matters on its own:
# a record with no state takes the first one, which is what opens an appointment in Draft.
STATES = (
	("Draft", "Danger"),
	("Pending Supervisor", "Warning"),
	("Pending GR Operator", "Warning"),
	("Pending Transportation Supervisor", "Warning"),
	("Set Pick-up as Accommodation (Supervisor)", "Warning"),
	("Pending PRO", "Warning"),
	("Rejected", "Primary"),
	("Completed", "Success"),
	("Reschedule Requested", "Danger"),
)

SUPERVISOR_RULE = "action_medical_appointment_supervisor.json"


def _fixture(folder, filename):
	return json.loads(
		frappe.read_file(frappe.get_app_path("one_fm", "custom", folder, filename))
	)


class TestTheStates(FrappeTestCase):
	def setUp(self):
		self.states = _fixture("workflow", "medical_appointment.json")["states"]

	def test_they_are_the_nine_the_analyst_lists_in_order(self):
		self.assertEqual([s["state"] for s in self.states], [name for name, _style in STATES])

	def test_an_appointment_opens_in_draft(self):
		"""A record inserted with no state takes the workflow's first one. The Preparation
		opens an appointment with no date, no transport decision and no PRO, so it must not
		land on a supervisor."""
		self.assertEqual(self.states[0]["state"], DRAFT)

	def test_every_state_carries_the_style_the_analyst_gave_it(self):
		"""Not decoration. create_workflow_state skips a state with no style, and the
		workflow save then dies on the missing link - both silently, leaving a workflow
		short of states on a fresh install."""
		self.assertEqual([(s["state"], s.get("style")) for s in self.states], list(STATES))

	def test_draft_is_editable_by_the_operator_who_fills_it_in(self):
		self.assertEqual(self.states[0]["allow_edit"], "Government Relations Operator")

	def test_draft_is_not_submitted(self):
		self.assertEqual(self.states[0]["doc_status"], "0")


class TestTheWayOutOfDraft(FrappeTestCase):
	def setUp(self):
		self.transitions = _fixture("workflow", "medical_appointment.json")["transitions"]

	def test_draft_has_one_action_and_it_is_the_analyst_s(self):
		"""An appointment opened in Draft with no action out of it is an appointment
		nobody can move."""
		out = [
			(t["state"], t["action"], t["next_state"])
			for t in self.transitions
			if t["state"] == DRAFT
		]
		self.assertEqual(out, [DRAFT_TRANSITION])

	def test_the_operator_moves_it_on(self):
		draft = next(t for t in self.transitions if t["state"] == DRAFT)
		self.assertEqual(draft["allowed"], "Government Relations Operator")
		self.assertEqual(draft["allow_self_approval"], 1)

	def test_nothing_else_was_touched(self):
		"""Thirteen transitions were already there; the story adds one."""
		self.assertEqual(len(self.transitions), 14)


class TestTheAssignmentRulesAreUnchanged(FrappeTestCase):
	"""The work item names the workflow and nothing else. A record in Draft was never
	assigned - the supervisor rule only fires from Pending Supervisor - so naming Draft in
	its unassign condition would be a change to configuration nobody asked to change."""

	def test_the_supervisor_rule_says_what_the_analyst_s_site_says(self):
		rule = _fixture("assignment_rule", SUPERVISOR_RULE)
		self.assertEqual(
			rule["assign_condition"],
			'workflow_state in ("Pending Supervisor", "Set Pick-up as Accommodation (Supervisor)")',
		)
		self.assertEqual(
			rule["unassign_condition"],
			'workflow_state in ("Pending GR Operator", "Pending Transportation Supervisor", '
			'"Pending PRO", "Rejected")',
		)
		self.assertNotIn(DRAFT, rule["unassign_condition"])
