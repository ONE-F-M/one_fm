# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for the Penalty And Investigation assignment rules (WI-001798).

One rule per waiting state of the WI-001796 workflow, shipped as supplied: "Based on
Field" on `owner`, assigning on workflow_state and closing when it moves on.
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
}

WORKFLOW = "Penalty & Investigation"

FIELDS = (
	"document_type", "priority", "disabled", "description",
	"is_assignment_rule_with_workflow", "assign_condition", "close_condition",
	"rule", "field",
)


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

	def test_they_select_the_assignee_from_a_field(self):
		for name in RULES:
			rule = _rule(name)
			self.assertEqual(rule.rule, "Based on Field", msg=name)
			self.assertEqual(rule.field, "owner", msg=name)

	def test_the_field_they_assign_on_exists(self):
		# Assigning on a missing field silently assigns to nobody.
		meta = frappe.get_meta("Penalty And Investigation")
		for name in RULES:
			field = _rule(name).field
			self.assertTrue(
				field in frappe.model.default_fields or meta.has_field(field), msg=field
			)

	def test_they_are_enabled_and_cover_every_day(self):
		for name in RULES:
			rule = _rule(name)
			self.assertFalse(rule.disabled, msg=name)
			self.assertEqual(len(rule.assignment_days), 7, msg=name)


class TestConditionsMatchTheWorkflow(FrappeTestCase):
	def test_every_state_they_wait_on_is_a_real_workflow_state(self):
		states = {d.state for d in frappe.get_doc("Workflow", WORKFLOW).states}
		for name, (_json_file, state) in RULES.items():
			self.assertIn(state, states, msg=name)

	def test_the_waiting_states_without_a_rule_are_known(self):
		"""Every state a penalty stops in wants an owner, but only three rules were
		supplied. Pending Payroll Officer arrived with WI-001796's updated criteria and
		has no rule of its own, so nobody is assigned when a penalty reaches payroll.
		Recorded here rather than invented: no rule for it exists in WI-001798.json.
		"""
		waiting = {
			d.state
			for d in frappe.get_doc("Workflow", WORKFLOW).states
			if d.state.startswith("Pending")
		}
		covered = {state for _f, state in RULES.values()}

		self.assertEqual(covered - waiting, set(), msg="a rule waits on a state that is gone")
		self.assertEqual(waiting - covered, {"Pending Payroll Officer"})

	def test_each_rule_names_its_own_state(self):
		for name, (_json_file, state) in RULES.items():
			rule = _rule(name)
			self.assertIn(f'== "{state}"', rule.assign_condition, msg=name)
			self.assertIn(f'!= "{state}"', rule.close_condition, msg=name)

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
			for condition in (rule.assign_condition, rule.close_condition or ""):
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
			for condition in (rule.assign_condition, rule.close_condition or ""):
				self.assertNotIn("doc.", condition, msg=name)

	def test_each_rule_assigns_on_its_own_state_and_closes_on_the_others(self):
		states = [d.state for d in frappe.get_doc("Workflow", WORKFLOW).states]
		for name, (_json_file, own_state) in RULES.items():
			rule = _rule(name)
			self.assertTrue(self._eval(rule.assign_condition, own_state), msg=name)
			self.assertFalse(self._eval(rule.close_condition, own_state), msg=name)
			for other in set(states) - {own_state}:
				self.assertFalse(self._eval(rule.assign_condition, other), msg=f"{name} on {other}")
				self.assertTrue(self._eval(rule.close_condition, other), msg=f"{name} on {other}")
