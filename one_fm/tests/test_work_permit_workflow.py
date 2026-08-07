# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-001974: the previous employer's answer to a Local Transfer is a workflow decision."""

import json

import frappe
from frappe.tests.utils import FrappeTestCase

WORKFLOW = "Work Permit"
WAITING_STATE = "Pending By Previous Company"


def _fixture():
	return json.loads(
		frappe.read_file(
			frappe.get_app_path("one_fm", "custom", "workflow", "work_permit.json")
		)
	)


def _transitions(source):
	return {(t["state"], t["action"], t["next_state"]) for t in source}


class TestThePreviousCompanyBranch(FrappeTestCase):
	def setUp(self):
		self.fixture = _transitions(_fixture()["transitions"])
		self.applied = _transitions(
			t.as_dict() for t in frappe.get_doc("Workflow", WORKFLOW).transitions
		)

	def test_the_previous_employer_can_refuse(self):
		"""The core of the work item: before this, a refusal had nowhere to go."""
		reject = (WAITING_STATE, "Reject", "Rejected")

		self.assertIn(reject, self.fixture)
		self.assertIn(reject, self.applied)

	def test_approval_still_moves_the_permit_on_to_pam(self):
		approve = (WAITING_STATE, "Approve", "Pending By PAM")

		self.assertIn(approve, self.fixture)
		self.assertIn(approve, self.applied)

	def test_the_old_one_way_action_is_gone(self):
		""""Informed Previous Company" could only move forward, which is why a refusal
		had no route. Leaving it beside Approve would offer the same step twice."""
		for transitions in (self.fixture, self.applied):
			self.assertEqual([t for t in transitions if t[1] == "Informed Previous Company"], [])

	def test_approval_is_only_offered_on_a_local_transfer(self):
		row = next(
			t for t in _fixture()["transitions"]
			if (t["state"], t["action"]) == (WAITING_STATE, "Approve")
		)

		self.assertIn("Local Transfer", row.get("condition") or "")

	def test_the_waiting_state_is_not_a_dead_end(self):
		"""Whatever the previous employer says, there is a way out."""
		out_of_waiting = {t[1] for t in self.applied if t[0] == WAITING_STATE}

		self.assertEqual(out_of_waiting, {"Approve", "Reject"})


class TestNoPermitIsLeftUnactionable(FrappeTestCase):
	def test_every_state_a_permit_holds_still_exists_in_the_workflow(self):
		"""A state the workflow no longer defines leaves that permit with no action."""
		defined = {s.state for s in frappe.get_doc("Workflow", WORKFLOW).states}
		held = {
			row.workflow_state
			for row in frappe.get_all(
				"Work Permit",
				filters={"workflow_state": ["is", "set"]},
				fields=["workflow_state"],
				distinct=True,
			)
		}

		self.assertEqual(held - defined, set())


class TestThePamRejectionIsOneStep(FrappeTestCase):
	"""WI-001827: PAM's refusal used to park in an intermediate state and need a second
	click to become Rejected."""

	RETIRED_STATE = "Reason of Rejection"

	def setUp(self):
		self.fixture = _transitions(_fixture()["transitions"])
		self.applied = _transitions(
			t.as_dict() for t in frappe.get_doc("Workflow", WORKFLOW).transitions
		)

	def test_pam_rejects_straight_to_rejected(self):
		reject = ("Pending By PAM", "Reject", "Rejected")

		self.assertIn(reject, self.fixture)
		self.assertIn(reject, self.applied)

	def test_the_two_step_route_is_gone(self):
		for transitions in (self.fixture, self.applied):
			self.assertEqual(
				[t for t in transitions if self.RETIRED_STATE in (t[0], t[2])], []
			)

	def test_the_reject_action_is_offered_once(self):
		"""BA's export carries the transition twice; two identical Reject buttons on the
		same state is a UI bug waiting to happen."""
		rejects = [
			t for t in _fixture()["transitions"]
			if (t["state"], t["action"]) == ("Pending By PAM", "Reject")
		]

		self.assertEqual(len(rejects), 1)

	def test_no_permit_is_left_in_the_retired_state(self):
		self.assertEqual(
			frappe.db.count("Work Permit", {"workflow_state": self.RETIRED_STATE}),
			0,
			msg="the patch should have moved these to Rejected",
		)

	def test_a_rejected_permit_can_still_say_why(self):
		"""The reason dropdowns (WI-001829) are what the retired state used to be for."""
		meta = frappe.get_meta("Work Permit")

		self.assertIsNotNone(meta.get_field("pam_rejection_reason"))
		self.assertIn(
			'reason_of_rejection == "Rejected by PAM"',
			meta.get_field("pam_rejection_reason").depends_on,
		)
