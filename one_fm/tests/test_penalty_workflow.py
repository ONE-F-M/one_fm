# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for the Penalty And Investigation workflow (WI-001796).

The table below is the supplied definition transcribed, so the workflow and the spec
cannot drift apart without a test failing.
"""

import frappe
from frappe.model.workflow import get_workflow_safe_globals
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


class TestRoutingConditions(FrappeTestCase):
	"""What the HR Administrator may do next, per the employee's answer and the salary
	tier (WI-001796). The conditions are evaluated the way Frappe evaluates them.
	"""

	PAYROLL_ANSWERS = ("Accepted", "Refused", "Not Return from Vacation")
	INVESTIGATION = "Request for Investigation by Employee"

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.wf = frappe.get_doc("Workflow", WORKFLOW)
		cls.routes = {
			(t.state, t.action): t for t in cls.wf.transitions if t.state == "Pending HR Administrator"
		}

	def _employee(self, above_threshold):
		operator = ">" if above_threshold else "between 1 and"
		return frappe.db.sql(
			f"""
			select name from `tabEmployee`
			where status = 'Active' and ifnull(one_fm_basic_salary, 0) {operator} 350 limit 1
			""",
			pluck=True,
		)

	def _allowed(self, action, issuance_status, employee):
		transition = self.routes[("Pending HR Administrator", action)]
		if not transition.condition:
			return True
		return bool(
			frappe.safe_eval(
				transition.condition,
				get_workflow_safe_globals(),
				{"doc": frappe._dict(issuance_status=issuance_status, employee=employee)},
			)
		)

	def test_the_three_routes_out_of_hr_carry_conditions(self):
		for action in ("Submit", "Submit to Legal", "Submit to GM"):
			self.assertTrue(self.routes[("Pending HR Administrator", action)].condition, msg=action)

	def test_put_on_hold_and_return_to_draft_stay_unconditional(self):
		# Nothing in the criteria gates them, and gating them could strand a penalty.
		for action in ("Put On Hold", "Return To Draft"):
			self.assertFalse(self.routes[("Pending HR Administrator", action)].condition, msg=action)

	def test_an_answered_penalty_goes_to_payroll(self):
		employee = self._employee(above_threshold=False)
		if not employee:
			self.skipTest("no Active employee within the salary threshold")
		for answer in self.PAYROLL_ANSWERS:
			self.assertTrue(self._allowed("Submit", answer, employee[0]), msg=answer)

	def test_an_answered_penalty_cannot_be_escalated_to_the_gm(self):
		# "the system prevents triggering the HR Administrator or Legal Investigation
		# sub-process, And the record can only be submitted directly to Payroll".
		employee = self._employee(above_threshold=False)
		if not employee:
			self.skipTest("no Active employee within the salary threshold")
		for answer in self.PAYROLL_ANSWERS:
			self.assertFalse(self._allowed("Submit to GM", answer, employee[0]), msg=answer)
			self.assertFalse(self._allowed("Submit to Legal", answer, employee[0]), msg=answer)

	def test_a_request_for_investigation_cannot_go_straight_to_payroll(self):
		employee = self._employee(above_threshold=False)
		if not employee:
			self.skipTest("no Active employee within the salary threshold")
		self.assertFalse(self._allowed("Submit", self.INVESTIGATION, employee[0]))
		self.assertTrue(self._allowed("Submit to Legal", self.INVESTIGATION, employee[0]))

	def test_the_higher_salary_tier_can_always_reach_legal(self):
		# "Given an employee's basic salary is more than 350 KD ... the task is routed
		# directly to the Legal Manager."
		employee = self._employee(above_threshold=True)
		if not employee:
			self.skipTest("no Active employee above the salary threshold")
		for answer in ("", self.INVESTIGATION, *self.PAYROLL_ANSWERS):
			self.assertTrue(self._allowed("Submit to Legal", answer, employee[0]), msg=answer)

	def test_an_unanswered_penalty_is_never_stuck(self):
		# With no answer recorded, payroll is closed but the GM route stays open, so the
		# penalty can always be moved on by someone.
		for above in (False, True):
			employee = self._employee(above_threshold=above)
			if not employee:
				continue
			self.assertFalse(self._allowed("Submit", "", employee[0]))
			self.assertTrue(self._allowed("Submit to GM", "", employee[0]))

	def test_every_answer_leaves_at_least_one_way_forward(self):
		for above in (False, True):
			employee = self._employee(above_threshold=above)
			if not employee:
				continue
			for answer in ("", self.INVESTIGATION, *self.PAYROLL_ANSWERS):
				available = [
					action
					for action in ("Submit", "Submit to Legal", "Submit to GM")
					if self._allowed(action, answer, employee[0])
				]
				self.assertTrue(available, msg=f"{answer!r} above={above} has nothing available")

	def test_the_conditions_read_the_field_that_exists(self):
		meta = frappe.get_meta(DOCTYPE)
		self.assertIsNotNone(meta.get_field("issuance_status"))
		options = {o for o in (meta.get_field("issuance_status").options or "").split("\n") if o}
		self.assertEqual(set(self.PAYROLL_ANSWERS) | {self.INVESTIGATION}, options)
