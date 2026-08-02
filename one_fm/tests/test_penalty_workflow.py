# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for the Penalty And Investigation workflow (WI-001796)."""

import frappe
from frappe.tests.utils import FrappeTestCase

WORKFLOW = "Penalty & Investigation"
DOCTYPE = "Penalty And Investigation"


class TestPenaltyWorkflow(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.wf = frappe.get_doc("Workflow", WORKFLOW)

	def test_exactly_one_active_workflow_governs_the_doctype(self):
		# Two active workflows on one doctype conflict, which is why the new definition
		# reuses the existing name rather than adding a second.
		active = frappe.get_all(
			"Workflow", filters={"document_type": DOCTYPE, "is_active": 1}, pluck="name"
		)
		self.assertEqual(active, [WORKFLOW])

	def test_every_state_is_declared_once(self):
		states = [s.state for s in self.wf.states]
		self.assertEqual(len(states), len(set(states)), msg=f"repeated state in {states}")

	def test_the_expected_states_exist(self):
		self.assertEqual(
			{s.state for s in self.wf.states},
			{
				"Draft", "Pending HR Administrator", "Pending Legal Manager",
				"Pending General Manager", "On Hold", "Approved", "Rejected", "Cancelled",
			},
		)

	def test_approved_is_the_submitted_state(self):
		# The offence count only counts approved penalties, and it filters on
		# docstatus 1, so Approved must be the submitted state.
		approved = next(s for s in self.wf.states if s.state == "Approved")
		self.assertEqual(int(approved.doc_status), 1)

	def test_cancelled_is_the_cancelled_state(self):
		cancelled = next(s for s in self.wf.states if s.state == "Cancelled")
		self.assertEqual(int(cancelled.doc_status), 2)

	def test_every_transition_connects_declared_states(self):
		declared = {s.state for s in self.wf.states}
		for t in self.wf.transitions:
			self.assertIn(t.state, declared, msg=f"{t.action} from an undeclared state")
			self.assertIn(t.next_state, declared, msg=f"{t.action} to an undeclared state")

	def test_every_role_a_transition_needs_exists(self):
		# A transition allowed to a non-existent role can never be actioned.
		for t in self.wf.transitions:
			self.assertTrue(
				frappe.db.exists("Role", t.allowed),
				msg=f"{t.action}: role {t.allowed!r} does not exist",
			)

	def test_each_reviewing_tier_can_reach_a_decision(self):
		by_state = {}
		for t in self.wf.transitions:
			by_state.setdefault(t.state, set()).add(t.next_state)
		# No pending state may be a dead end.
		for state in ("Pending HR Administrator", "Pending Legal Manager", "Pending General Manager"):
			self.assertTrue(by_state.get(state), msg=f"{state} has no outgoing transition")

	def test_legal_and_gm_tiers_are_reachable(self):
		targets = {t.next_state for t in self.wf.transitions}
		self.assertIn("Pending Legal Manager", targets)
		self.assertIn("Pending General Manager", targets)

	def test_no_record_is_stranded_in_a_retired_state(self):
		declared = {s.state for s in self.wf.states}
		stranded = frappe.db.sql(
			"""
			select ifnull(workflow_state, '') as state, count(*) as n
			from `tabPenalty And Investigation`
			group by workflow_state
			""",
			as_dict=True,
		)
		orphans = {r.state: r.n for r in stranded if r.state and r.state not in declared}
		self.assertEqual(orphans, {}, msg=f"records left in retired states: {orphans}")
