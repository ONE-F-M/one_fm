# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for the Penalty And Investigation workflow (WI-001796).

The table below is the supplied definition transcribed, so the workflow and the spec
cannot drift apart without a test failing.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.custom.workflow.workflow import get_workflow_json_file

WORKFLOW = "Penalty & Investigation"
DOCTYPE = "Penalty And Investigation"
WORKFLOW_FILE = "penalty_and_investigation.json"

STATE_FIELDS = ("state", "doc_status", "style", "allow_edit", "send_email")
TRANSITION_FIELDS = ("state", "action", "next_state", "allowed", "allow_self_approval")

# (from state, action, to state, allowed role)
SUPPLIED_TRANSITIONS = {
	("Draft", "Submit", "Pending HR Administrator", "HR User"),
	("Pending HR Administrator", "Put On Hold", "On Hold", "HR User"),
	("Pending HR Administrator", "Return To Draft", "Draft", "HR User"),
	("Pending HR Administrator", "Submit to GM", "Pending General Manager", "HR User"),
	("Pending HR Administrator", "Submit", "Pending Payroll Officer", "HR User"),
	("Pending HR Administrator", "Submit to Legal", "Pending Legal Manager", "HR User"),
	("Pending Legal Manager", "Submit to GM", "Pending General Manager", "Legal Manager"),
	("Pending General Manager", "Submit", "Pending Payroll Officer", "General Manager"),
	("Pending General Manager", "Reject", "Rejected", "General Manager"),
	("Pending Payroll Officer", "Cancel", "Cancelled", "HR User"),
	("On Hold", "Approve", "Pending Payroll Officer", "HR User"),
	("On Hold", "Reject", "Rejected", "HR User"),
	("Pending Payroll Officer", "Submit", "Completed", "Payroll Operator"),
}

# state -> doc_status, as supplied. Cancelled is declared twice with different edit
# roles; both carry 2, so the first-match lookup Frappe does is unambiguous here.
SUPPLIED_DOC_STATUS = {
	"Draft": 0,
	"Pending HR Administrator": 0,
	"Pending General Manager": 0,
	"Pending Legal Manager": 0,
	"Cancelled": 2,
	"Completed": 1,
	"Rejected": 0,
	"On Hold": 0,
	"Pending Payroll Officer": 1,
}


class TestPenaltyWorkflow(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.wf = frappe.get_doc("Workflow", WORKFLOW)

	def test_exactly_one_active_workflow_governs_the_doctype(self):
		# Two active workflows on one doctype conflict, which is why the definition
		# reuses the existing name rather than adding a second.
		active = frappe.get_all(
			"Workflow", filters={"document_type": DOCTYPE, "is_active": 1}, pluck="name"
		)
		self.assertEqual(active, [WORKFLOW])

	def test_the_applied_workflow_matches_the_shipped_definition(self):
		"""Field for field and in order, including the two Cancelled rows the definition
		declares: Frappe puts no unique constraint on Workflow Document State.state and
		reads the first match, so the second row is inert, and dropping it would be an
		edit to the spec rather than a fix.
		"""
		definition = get_workflow_json_file(WORKFLOW_FILE)

		self.assertEqual(
			[[str(row.get(f) or "") for f in STATE_FIELDS] for row in definition["states"]],
			[[str(row.get(f) or "") for f in STATE_FIELDS] for row in self.wf.states],
		)
		self.assertEqual(
			[[str(row.get(f) or "") for f in TRANSITION_FIELDS] for row in definition["transitions"]],
			[[str(row.get(f) or "") for f in TRANSITION_FIELDS] for row in self.wf.transitions],
		)

	def test_every_supplied_transition_exists_and_nothing_else_does(self):
		applied = {(t.state, t.action, t.next_state, t.allowed) for t in self.wf.transitions}
		self.assertEqual(SUPPLIED_TRANSITIONS - applied, set(), msg="missing from the workflow")
		self.assertEqual(applied - SUPPLIED_TRANSITIONS, set(), msg="not in the definition")

	def test_each_state_carries_the_docstatus_it_was_given(self):
		for state in self.wf.states:
			self.assertEqual(
				int(state.doc_status), SUPPLIED_DOC_STATUS[state.state], msg=state.state
			)

	def test_payroll_holds_a_submitted_document(self):
		# Pending Payroll Officer is docstatus 1, which is what makes Cancel -> Cancelled
		# legal: Frappe refuses a 0 -> 2 transition ("Cannot cancel before submitting").
		# It also means the penalty is locked from Submit onwards, not only at Completed.
		self.assertEqual(SUPPLIED_DOC_STATUS["Pending Payroll Officer"], 1)
		self.assertEqual(SUPPLIED_DOC_STATUS["Cancelled"], 2)

	def test_no_transition_breaks_frappes_docstatus_rules(self):
		# The same checks Workflow.validate_docstatus() runs, so a bad pairing fails here
		# rather than on a site.
		for t in self.wf.transitions:
			frm, to = SUPPLIED_DOC_STATUS[t.state], SUPPLIED_DOC_STATUS[t.next_state]
			self.assertNotEqual(frm, 2, msg=f"{t.action} leaves a cancelled state")
			self.assertFalse(frm == 1 and to == 0, msg=f"{t.action}: submitted -> draft")
			self.assertFalse(frm == 0 and to == 2, msg=f"{t.action}: cancel before submit")

	def test_the_offence_count_only_counts_a_finished_penalty(self):
		# WI-001794 counts a prior offence as docstatus 1 AND an approved state. Payroll
		# is also docstatus 1, so the state list is what keeps a penalty that is merely
		# awaiting payroll out of the count.
		from one_fm.legal.doctype.penalty_and_investigation.penalty_and_investigation import (
			APPROVED_STATES,
		)

		self.assertIn("Completed", APPROVED_STATES)
		self.assertNotIn("Pending Payroll Officer", APPROVED_STATES)

	def test_nothing_leaves_completed(self):
		self.assertEqual([t.action for t in self.wf.transitions if t.state == "Completed"], [])

	def test_every_transition_allows_self_approval(self):
		for t in self.wf.transitions:
			self.assertTrue(t.allow_self_approval, msg=t.action)

	def test_every_state_alerts_by_email(self):
		for s in self.wf.states:
			self.assertTrue(s.send_email, msg=s.state)

	def test_every_transition_connects_declared_states(self):
		declared = {s.state for s in self.wf.states}
		for t in self.wf.transitions:
			self.assertIn(t.state, declared, msg=f"{t.action} from an undeclared state")
			self.assertIn(t.next_state, declared, msg=f"{t.action} to an undeclared state")

	def test_every_role_a_transition_needs_exists(self):
		# A transition allowed to a non-existent role can never be actioned. The
		# definition names Payroll Operator, which is the role that exists - there is no
		# "Payroll Officer" role, only the state of that name.
		for t in self.wf.transitions:
			self.assertTrue(
				frappe.db.exists("Role", t.allowed),
				msg=f"{t.action}: role {t.allowed!r} does not exist",
			)

	def test_every_state_that_waits_can_reach_a_decision(self):
		by_state = {}
		for t in self.wf.transitions:
			by_state.setdefault(t.state, set()).add(t.next_state)
		for state in (
			"Draft",
			"Pending HR Administrator",
			"Pending Legal Manager",
			"Pending General Manager",
			"Pending Payroll Officer",
			"On Hold",
		):
			self.assertTrue(by_state.get(state), msg=f"{state} has no outgoing transition")

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


class TestSalaryRoutingIsManual(FrappeTestCase):
	"""The definition carries no transition conditions, so the salary tier this story is
	named for is not evaluated by the workflow (WI-001796).

	Recorded rather than added to: Draft has a single unconditional Submit to the HR
	Administrator, and the >350 KD route is reached by an HR User pressing
	"Submit to Legal". If that split is meant to be automatic it needs a condition on
	these transitions.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.wf = frappe.get_doc("Workflow", WORKFLOW)

	def test_no_transition_carries_a_condition(self):
		self.assertEqual([t.action for t in self.wf.transitions if t.condition], [])

	def test_draft_submits_only_to_the_hr_administrator(self):
		submits = [t for t in self.wf.transitions if t.state == "Draft" and t.action == "Submit"]
		self.assertEqual([t.next_state for t in submits], ["Pending HR Administrator"])

	def test_legal_is_reachable_from_the_hr_administrator(self):
		# So a >350 KD penalty can still get to Legal, by hand.
		routes = {(t.state, t.action): t.next_state for t in self.wf.transitions}
		self.assertEqual(
			routes[("Pending HR Administrator", "Submit to Legal")], "Pending Legal Manager"
		)
