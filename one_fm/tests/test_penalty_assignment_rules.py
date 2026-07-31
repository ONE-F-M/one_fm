# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for the Penalty And Investigation assignment rules (WI-001798).

One rule per waiting state of the WI-001796 workflow: the penalty sits with the HR
Administrator, the Legal Manager or the General Manager, and hands over as the
workflow moves on.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.safe_exec import get_safe_globals

RULES = {
	"Penalty and Investigation-HR Administrator": "Pending HR Administrator",
	"Penalty and Investigation-Legal Manager": "Pending Legal Manager",
	"Penalty and Investigation-General Manager": "Pending General Manager",
}

WORKFLOW = "Penalty & Investigation"


def _rule(name):
	if not frappe.db.exists("Assignment Rule", name):
		return None
	return frappe.get_doc("Assignment Rule", name)


class TestRulesExist(FrappeTestCase):
	def test_every_tier_has_a_rule(self):
		for name in RULES:
			self.assertTrue(frappe.db.exists("Assignment Rule", name), msg=name)

	def test_they_are_enabled_and_cover_every_day(self):
		for name in RULES:
			rule = _rule(name)
			self.assertFalse(rule.disabled, msg=name)
			self.assertEqual(len(rule.assignment_days), 7, msg=name)

	def test_they_resolve_the_assignee_from_a_process_task(self):
		# "Based on Process Task" with no task linked assigns nobody at all.
		for name in RULES:
			rule = _rule(name)
			self.assertEqual(rule.rule, "Based on Process Task", msg=name)
			self.assertTrue(rule.custom_routine_task, msg=name)

	def test_each_process_task_points_at_a_user(self):
		for name in RULES:
			user = frappe.db.get_value(
				"Process Task", _rule(name).custom_routine_task, "employee_user"
			)
			self.assertTrue(user, msg=name)
			self.assertTrue(frappe.db.exists("User", user), msg=name)

	def test_they_carry_the_workflow_action_buttons(self):
		for name in RULES:
			self.assertTrue(_rule(name).is_assignment_rule_with_workflow, msg=name)


class TestConditionsMatchTheWorkflow(FrappeTestCase):
	def test_every_state_they_wait_on_is_a_real_workflow_state(self):
		states = {d.state for d in frappe.get_doc("Workflow", WORKFLOW).states}
		for name, state in RULES.items():
			self.assertIn(state, states, msg=name)

	def test_no_waiting_state_is_left_unassigned(self):
		# Any state a penalty can stop in and wait for a decision needs an owner.
		waiting = {
			d.state
			for d in frappe.get_doc("Workflow", WORKFLOW).states
			if d.state.startswith("Pending")
		}
		self.assertEqual(waiting, set(RULES.values()))


class TestConditionsAreEvaluable(FrappeTestCase):
	"""Conditions run through safe_eval with the document as locals."""

	def _eval(self, condition, doc):
		return frappe.safe_eval(condition, get_safe_globals(), doc)

	def test_no_condition_reaches_for_a_doc_prefix(self):
		# "doc.workflow_state" is a NameError here, and safe_eval swallows it - the
		# rule then silently never fires.
		for name in RULES:
			rule = _rule(name)
			for condition in (rule.assign_condition, rule.unassign_condition or ""):
				self.assertNotIn("doc.", condition, msg=name)

	def test_each_rule_fires_on_its_own_state_only(self):
		for name, state in RULES.items():
			rule = _rule(name)
			self.assertTrue(self._eval(rule.assign_condition, {"workflow_state": state}))
			for other in set(RULES.values()) - {state}:
				self.assertFalse(
					self._eval(rule.assign_condition, {"workflow_state": other}), msg=other
				)

	def test_each_rule_releases_the_penalty_when_it_moves_on(self):
		# Frappe only lets the next tier assign once the previous one has unassigned,
		# so an unassign condition - not just a close condition - is what hands over.
		for name, state in RULES.items():
			rule = _rule(name)
			self.assertTrue(rule.unassign_condition, msg=name)
			self.assertFalse(self._eval(rule.unassign_condition, {"workflow_state": state}))
			self.assertTrue(self._eval(rule.unassign_condition, {"workflow_state": "Approved"}))

	def test_the_notification_only_renders_fields_the_penalty_has(self):
		meta = frappe.get_meta("Penalty And Investigation")
		for name in RULES:
			for fieldname in ("issuer", "employee"):
				self.assertIn("{{" + fieldname + "}}", _rule(name).description, msg=name)
				self.assertTrue(meta.has_field(fieldname), msg=fieldname)
