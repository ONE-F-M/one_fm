# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for the Penalty And Investigation workflow (WI-001796).

The states and transitions are transcribed from the acceptance criteria, so the table
below is the specification: if the workflow drifts from it, these fail.
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

# The acceptance criteria, as a table: (from state, action, to state, allowed role).
AC_TRANSITIONS = {
	("Draft", "Submit", "Pending HR Administrator", "HR User"),
	("Draft", "Submit", "Pending Legal Manager", "HR User"),
	("Pending HR Administrator", "Submit", "Pending Payroll Officer", "HR User"),
	("Pending HR Administrator", "Submit to Legal", "Pending Legal Manager", "HR User"),
	("Pending HR Administrator", "Submit to GM", "Pending General Manager", "HR User"),
	("Pending HR Administrator", "Return To Draft", "Draft", "HR User"),
	("Pending HR Administrator", "Put On Hold", "On Hold", "HR User"),
	("Pending Legal Manager", "Submit to GM", "Pending General Manager", "Legal Manager"),
	("Pending General Manager", "Submit", "Pending Payroll Officer", "General Manager"),
	("Pending General Manager", "Reject", "Rejected", "General Manager"),
	("Pending Payroll Officer", "Submit", "Completed", "Payroll Operator"),
	("Pending Payroll Officer", "Cancel", "Canceled", "HR User"),
	("On Hold", "Approve", "Pending Payroll Officer", "HR User"),
	("On Hold", "Reject", "Rejected", "HR User"),
}

SALARY_THRESHOLD = 350


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
		definition = get_workflow_json_file(WORKFLOW_FILE)

		self.assertEqual(
			[[str(row.get(f) or "") for f in STATE_FIELDS] for row in definition["states"]],
			[[str(row.get(f) or "") for f in STATE_FIELDS] for row in self.wf.states],
		)
		self.assertEqual(
			[[str(row.get(f) or "") for f in TRANSITION_FIELDS] for row in definition["transitions"]],
			[[str(row.get(f) or "") for f in TRANSITION_FIELDS] for row in self.wf.transitions],
		)

	def test_every_transition_the_criteria_describe_exists(self):
		applied = {(t.state, t.action, t.next_state, t.allowed) for t in self.wf.transitions}
		self.assertEqual(AC_TRANSITIONS - applied, set(), msg="missing from the workflow")
		self.assertEqual(applied - AC_TRANSITIONS, set(), msg="not in the criteria")

	def test_completed_is_the_submitted_state(self):
		# "the document is permanently locked and marked complete". The offence count in
		# WI-001794 also filters on docstatus 1.
		completed = next(s for s in self.wf.states if s.state == "Completed")
		self.assertEqual(int(completed.doc_status), 1)

	def test_nothing_leaves_completed(self):
		self.assertEqual([t.action for t in self.wf.transitions if t.state == "Completed"], [])

	def test_canceled_is_reachable_from_payroll(self):
		# Frappe refuses a docstatus 0 -> 2 transition ("Cannot cancel before
		# submitting"), and the criteria put Cancel on Pending Payroll Officer, which is
		# a draft state - so Canceled cannot carry docstatus 2. Excluding it from
		# payroll and from the 12-month count is done by state, not by docstatus.
		canceled = next(s for s in self.wf.states if s.state == "Canceled")
		self.assertEqual(int(canceled.doc_status), 0)

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
		# criteria say "Payroll Operator" acts on Pending Payroll Officer, and that is
		# the role that exists - there is no "Payroll Officer" role.
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


class TestSalaryThresholdRouting(FrappeTestCase):
	"""Draft's Submit routes on the employee's basic salary (WI-001796)."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.wf = frappe.get_doc("Workflow", WORKFLOW)
		cls.submits = [
			t for t in cls.wf.transitions if t.state == "Draft" and t.action == "Submit"
		]

	def _eval(self, condition, employee):
		return frappe.safe_eval(
			condition, get_workflow_safe_globals(), {"doc": frappe._dict(employee=employee)}
		)

	def _employee_with_salary(self, above):
		operator = ">" if above else "<="
		return frappe.db.sql(
			f"""
			select name from `tabEmployee`
			where status = 'Active' and ifnull(one_fm_basic_salary, 0) {operator} %s
			  and ifnull(one_fm_basic_salary, 0) > 0
			limit 1
			""",
			SALARY_THRESHOLD,
			pluck=True,
		)

	def test_both_tiers_are_routed_from_draft(self):
		self.assertEqual(
			{t.next_state for t in self.submits},
			{"Pending HR Administrator", "Pending Legal Manager"},
		)

	def test_each_route_carries_a_condition(self):
		# Without one, Frappe would take whichever transition it read first.
		for t in self.submits:
			self.assertTrue(t.condition, msg=t.next_state)

	def test_the_tiers_are_mutually_exclusive(self):
		for above in (False, True):
			employee = self._employee_with_salary(above)
			if not employee:
				self.skipTest(f"no Active employee with a salary {'above' if above else 'within'} the threshold")
			results = {t.next_state: self._eval(t.condition, employee[0]) for t in self.submits}
			self.assertEqual(
				sum(1 for taken in results.values() if taken), 1, msg=f"{employee[0]}: {results}"
			)

	def test_the_lower_tier_goes_to_hr_and_the_higher_to_legal(self):
		within = self._employee_with_salary(above=False)
		above = self._employee_with_salary(above=True)
		if not (within and above):
			self.skipTest("needs an Active employee on each side of the threshold")

		routes = {t.next_state: t.condition for t in self.submits}
		self.assertTrue(self._eval(routes["Pending HR Administrator"], within[0]))
		self.assertTrue(self._eval(routes["Pending Legal Manager"], above[0]))

	def test_an_unset_salary_stays_with_hr(self):
		# 67 Active employees carry no basic salary. Reading as 0 keeps them in the
		# cheaper tier rather than sending them to Legal by accident.
		employee = frappe.db.sql(
			"""
			select name from `tabEmployee`
			where status = 'Active' and ifnull(one_fm_basic_salary, 0) = 0 limit 1
			""",
			pluck=True,
		)
		if not employee:
			self.skipTest("every Active employee has a basic salary on this instance")

		routes = {t.next_state: t.condition for t in self.submits}
		self.assertTrue(self._eval(routes["Pending HR Administrator"], employee[0]))
		self.assertFalse(self._eval(routes["Pending Legal Manager"], employee[0]))
