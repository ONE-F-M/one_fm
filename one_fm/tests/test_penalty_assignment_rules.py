# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for the Penalty And Investigation assignment rules (WI-001798, WI-001838).

One rule per waiting state of the WI-001796 workflow, assigning on workflow_state and
closing when it moves on. WI-001838 changed how they pick the assignee: "Based on
Process Task" instead of "Based on Field" on `owner`, so the process owner can hand a
tier to someone else from the Process Task without a code change.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.custom.assignment_rule.assignment_rule import get_assignment_rule_json_file

RULES = {
	"Penalty and Investigation-HR Administrator": (
		"penalty_and_investigation_hr_administrator.json",
		"Pending HR Administrator",
	),
	"Penalty and Investigation-Legal Manager": (
		"penalty_and_investigation_legal_manager.json",
		"Pending Legal Manager",
	),
	"Penalty and Investigation-General Manager": (
		"penalty_and_investigation_general_manager.json",
		"Pending General Manager",
	),
	"Penalty and Investigation-Payroll Officer": (
		"penalty_and_investigation_payroll_officer.json",
		"Pending Payroll Officer",
	),
}

# The Process Task each rule now takes its assignee from (WI-001838).
PROCESS_NAME = "Penalty"

TASKS = {
	"Penalty and Investigation-HR Administrator": "Assigning HR Administrator",
	"Penalty and Investigation-Legal Manager": "Assigning Legal Manager",
	"Penalty and Investigation-General Manager": "Assigning General Manager",
	"Penalty and Investigation-Payroll Officer": "Assigning Payroll Officer",
}

WORKFLOW = "Penalty & Investigation"

FIELDS = (
	"document_type", "priority", "disabled", "description",
	"is_assignment_rule_with_workflow", "assign_condition", "close_condition",
	"rule", "field",
)


def _conditions(rule):
	"""Every condition the rule actually carries, skipping the ones left empty."""
	return [
		c
		for c in (rule.assign_condition, rule.unassign_condition, rule.close_condition)
		if c
	]


def _rule(name):
	if not frappe.db.exists("Assignment Rule", name):
		return None
	return frappe.get_doc("Assignment Rule", name)


class TestRulesMatchWhatWasSupplied(FrappeTestCase):
	def test_every_tier_has_a_rule(self):
		for name in RULES:
			self.assertTrue(frappe.db.exists("Assignment Rule", name), msg=name)

	def test_each_rule_is_applied_field_for_field(self):
		# The supplied definition is the spec; this fails if the fixture or the saved
		# rule drifts from it.
		for name, (json_file, _state) in RULES.items():
			supplied = get_assignment_rule_json_file(json_file)
			applied = _rule(name)
			for field in FIELDS:
				self.assertEqual(
					str(supplied.get(field) or ""),
					str(applied.get(field) or ""),
					msg=f"{name}.{field}",
				)

	def test_they_select_the_assignee_from_a_process_task(self):
		for name in RULES:
			self.assertEqual(_rule(name).rule, "Based on Process Task", msg=name)

	def test_they_are_enabled_and_cover_every_day(self):
		for name in RULES:
			rule = _rule(name)
			self.assertFalse(rule.disabled, msg=name)
			self.assertEqual(len(rule.assignment_days), 7, msg=name)


class TestTheProcessTaskTheyAssignThrough(FrappeTestCase):
	"""WI-001838. `get_user_based_on_process_task` reads one field - the linked task's
	`employee_user` - and returns it with no fallback, so an unlinked rule or a task
	whose employee has no user assigns nobody and the penalty just sits there.
	"""

	def test_every_rule_is_linked_to_a_process_task(self):
		for name in RULES:
			self.assertTrue(_rule(name).custom_routine_task, msg=name)

	def test_the_linked_task_exists_and_is_the_one_for_that_tier(self):
		for name, task in TASKS.items():
			linked = _rule(name).custom_routine_task
			self.assertTrue(frappe.db.exists("Process Task", linked), msg=name)
			self.assertEqual(
				frappe.db.get_value("Process Task", linked, ["process_name", "task"]),
				(PROCESS_NAME, task),
				msg=name,
			)

	def test_no_two_tiers_share_a_task(self):
		# Two rules on one task means both tiers land on the same person, which is the
		# owner-assignment problem WI-001838 set out to remove.
		linked = [_rule(name).custom_routine_task for name in RULES]
		self.assertEqual(len(set(linked)), len(linked), msg=linked)

	def test_the_task_resolves_to_a_user_who_can_be_assigned(self):
		for name in RULES:
			user = frappe.db.get_value(
				"Process Task", _rule(name).custom_routine_task, "employee_user"
			)
			# A disabled user is not asserted against: assign_to still writes the ToDo and
			# only skips the notification, so it is a data question for the process owner,
			# not something this rule can get wrong.
			self.assertTrue(user, msg=f"{name}: task names no employee_user")
			self.assertTrue(frappe.db.exists("User", user), msg=f"{name}: {user}")

	def test_the_rule_hands_back_that_user(self):
		# The path the framework takes when a penalty enters the waiting state. The
		# selection ignores the document now, so the tier's assignee no longer depends on
		# who raised the penalty - which is the whole point of the change.
		for name, state in ((n, s) for n, (_f, s) in RULES.items()):
			rule = _rule(name)
			expected = frappe.db.get_value(
				"Process Task", rule.custom_routine_task, "employee_user"
			)
			doc = frappe._dict(
				doctype="Penalty And Investigation", workflow_state=state, owner="Administrator"
			)
			self.assertEqual(rule.get_user(doc), expected, msg=name)
			self.assertNotEqual(rule.get_user(doc), doc.owner, msg=name)

	def test_the_linked_task_is_active(self):
		for name in RULES:
			self.assertTrue(
				frappe.db.get_value("Process Task", _rule(name).custom_routine_task, "is_active"),
				msg=name,
			)


class TestConditionsMatchTheWorkflow(FrappeTestCase):
	def test_every_state_they_wait_on_is_a_real_workflow_state(self):
		states = {d.state for d in frappe.get_doc("Workflow", WORKFLOW).states}
		for name, (_json_file, state) in RULES.items():
			self.assertIn(state, states, msg=name)

	def test_no_waiting_state_is_left_unassigned(self):
		# Every state a penalty stops in and waits for a decision needs an owner. Payroll
		# arrived with WI-001796's updated criteria and now has a rule of its own.
		waiting = {
			d.state
			for d in frappe.get_doc("Workflow", WORKFLOW).states
			if d.state.startswith("Pending")
		}
		covered = {state for _f, state in RULES.values()}

		self.assertEqual(covered - waiting, set(), msg="a rule waits on a state that is gone")
		self.assertEqual(waiting - covered, set(), msg="a waiting state has no rule")

	def test_each_rule_names_its_own_state(self):
		# The supplied definition leaves close_condition empty and does the work in
		# unassign_condition, which is the one AssignmentRule.apply_unassign evaluates.
		for name, (_json_file, state) in RULES.items():
			rule = _rule(name)
			self.assertIn(f'== "{state}"', rule.assign_condition, msg=name)
			self.assertIn(f'!= "{state}"', rule.unassign_condition, msg=name)

	def test_the_notification_only_renders_fields_the_penalty_has(self):
		meta = frappe.get_meta("Penalty And Investigation")
		for name in RULES:
			for fieldname in ("issuer", "employee"):
				self.assertIn("{{" + fieldname + "}}", _rule(name).description, msg=name)
				self.assertTrue(meta.has_field(fieldname), msg=fieldname)


class TestConditionsActuallyEvaluate(FrappeTestCase):
	"""Frappe evaluates an assignment rule's condition with the document itself as the
	eval locals - `frappe.safe_eval(condition, None, doc)` - so a name that is not a
	field on the document raises, AssignmentRule.safe_eval swallows it into an "Auto
	assignment failed" message, and the rule silently never fires.
	"""

	def _eval(self, condition, workflow_state):
		# The same call the framework makes, with the same locals.
		return frappe.safe_eval(condition, None, frappe._dict(workflow_state=workflow_state))

	def test_no_condition_raises_for_any_state_of_the_workflow(self):
		states = [d.state for d in frappe.get_doc("Workflow", WORKFLOW).states]
		for name in RULES:
			rule = _rule(name)
			for condition in _conditions(rule):
				if not condition:
					continue
				for state in states + [None, ""]:
					try:
						self._eval(condition, state)
					except Exception as e:
						self.fail(f"{name}: {condition!r} on {state!r} raised {type(e).__name__}: {e}")

	def test_no_condition_reaches_for_a_name_the_document_does_not_carry(self):
		# "doc.workflow_state" is the trap: valid in a workflow transition condition,
		# which is handed {"doc": ...}, but a NameError here.
		for name in RULES:
			rule = _rule(name)
			for condition in _conditions(rule):
				self.assertNotIn("doc.", condition, msg=name)

	def test_each_rule_assigns_on_its_own_state_and_releases_on_the_others(self):
		states = [d.state for d in frappe.get_doc("Workflow", WORKFLOW).states]
		for name, (_json_file, own_state) in RULES.items():
			rule = _rule(name)
			self.assertTrue(self._eval(rule.assign_condition, own_state), msg=name)
			self.assertFalse(self._eval(rule.unassign_condition, own_state), msg=name)
			for other in set(states) - {own_state}:
				self.assertFalse(self._eval(rule.assign_condition, other), msg=f"{name} on {other}")
				self.assertTrue(self._eval(rule.unassign_condition, other), msg=f"{name} on {other}")


class TestAssignmentDays(FrappeTestCase):
	def test_every_rule_covers_all_seven_days(self):
		for name in RULES:
			self.assertEqual(
				[d.day for d in _rule(name).assignment_days],
				["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
				msg=name,
			)

	def test_the_fixtures_do_not_pin_child_row_names(self):
		# Frappe names child rows on insert. A name carried over from the site the rule
		# was exported from is an artefact, and reusing one risks colliding with a row
		# that already exists.
		for _name, (json_file, _state) in RULES.items():
			for row in get_assignment_rule_json_file(json_file)["assignment_days"]:
				self.assertNotIn("name", row, msg=json_file)
