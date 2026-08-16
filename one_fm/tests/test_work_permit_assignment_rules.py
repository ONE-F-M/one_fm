# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-001827: the three Work Permit assignment rules the work item links to."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0.add_work_permit_assignment_rules import RULES

PAYMENT_STATE = "Pending  For Payment"  # two spaces, as the workflow spells it

OPERATOR_STATES = (
	'["Apply Online by PRO", "Pending By PAM", "Pending By Previous Company", '
	'"Pending By Operator", "Reason of Rejection"]'
)

# The export the work item links to, with the three corrections it needs to work at all:
# `doc.workflow_state` -> `workflow_state`, the payment state spelt with both its spaces,
# and the states a rule merely hands over in moved from close_condition to
# unassign_condition. These pin the rules against drift: what is applied has to match,
# field for field.
EXPORTED = {
	"Work Permit-PRO": {
		"assign_condition": 'workflow_state == "Apply Online by PRO"',
		"unassign_condition": 'workflow_state != "Apply Online by PRO"',
		"close_condition": None,
	},
	"Work Permit - GRD Supervisor": {
		"assign_condition": f'workflow_state in ["Pending By Supervisor", "{PAYMENT_STATE}"]',
		"unassign_condition": f'workflow_state not in ["Pending By Supervisor", "{PAYMENT_STATE}"]',
		"close_condition": None,
	},
	"Work Permit - GR Operator": {
		"assign_condition": f"workflow_state in {OPERATOR_STATES}",
		"unassign_condition": f"workflow_state not in {OPERATOR_STATES}",
		"close_condition": 'workflow_state in ["Completed", "Rejected"]',
	},
}


def _rule(name):
	return frappe.get_doc("Assignment Rule", name)


def _states():
	return [s.state for s in frappe.get_doc("Workflow", "Work Permit").states]


class TestTheRulesExist(FrappeTestCase):
	def test_all_three_are_there_and_enabled(self):
		for rule in RULES:
			doc = _rule(rule["name"])

			self.assertEqual(doc.document_type, "Work Permit", msg=rule["name"])
			self.assertFalse(doc.disabled, msg=rule["name"])

	def test_the_conditions_are_the_exported_ones(self):
		for name, conditions in EXPORTED.items():
			doc = _rule(name)

			for field, expected in conditions.items():
				self.assertEqual(doc.get(field) or None, expected, msg=f"{name}.{field}")

	def test_only_the_terminal_states_close_assignments(self):
		"""close_condition closes every assignment on the document, whichever rule made it
		(close_assignments -> assign_to.close_all_assignments), and apply() runs it for
		every rule. So a rule may only close where nobody should hold the permit at all -
		anything else belongs in unassign_condition, which fires only for the rule that
		owns the assignment."""
		for rule in RULES:
			condition = _rule(rule["name"]).close_condition
			if not condition:
				continue

			for state in _states():
				if state in ("Completed", "Rejected", "Cancelled"):
					continue
				self.assertFalse(
					frappe.safe_eval(condition, None, {"workflow_state": state}),
					msg=f"{rule['name']} closes everyone's assignments at {state!r}",
				)

	def test_each_takes_its_assignee_from_a_process_task(self):
		"""Rule type is "Based on Process Task", so an unlinked rule assigns nobody."""
		for rule in RULES:
			doc = _rule(rule["name"])

			self.assertEqual(doc.rule, "Based on Process Task", msg=rule["name"])
			self.assertTrue(doc.custom_routine_task, msg=rule["name"])

			task = frappe.db.get_value(
				"Process Task", doc.custom_routine_task, ["task", "employee_user"], as_dict=True
			)
			self.assertEqual(task.task, rule["task"], msg=rule["name"])
			self.assertTrue(task.employee_user, msg=f"{rule['name']}: task has no user to assign")

	def test_the_three_tasks_are_not_the_same_task(self):
		linked = {_rule(rule["name"]).custom_routine_task for rule in RULES}

		self.assertEqual(len(linked), len(RULES))


class TestTheConditionsActuallyRun(FrappeTestCase):
	"""assign_condition is eval'd as safe_eval(condition, None, doc.as_dict()) - the
	document's own fields are the locals, and anything that raises is swallowed into an
	"Auto assignment failed" msgprint, leaving the rule silently dead."""

	def conditions(self):
		for rule in RULES:
			doc = _rule(rule["name"])
			for field in ("assign_condition", "close_condition", "unassign_condition"):
				if doc.get(field):
					yield rule["name"], field, doc.get(field)

	def test_no_condition_raises_on_any_state_a_permit_can_hold(self):
		"""The export tested `doc.workflow_state`, where `doc` is not a name in scope."""
		for name, field, condition in self.conditions():
			for state in _states():
				try:
					frappe.safe_eval(condition, None, {"workflow_state": state})
				except Exception as e:
					self.fail(f"{name}.{field} on {state!r}: {type(e).__name__}: {e}")

	def test_the_operator_is_assigned_at_pam_and_released_once_it_is_over(self):
		doc = _rule("Work Permit - GR Operator")

		self.assertTrue(
			frappe.safe_eval(doc.assign_condition, None, {"workflow_state": "Pending By PAM"})
		)
		for done in ("Completed", "Rejected"):
			self.assertTrue(
				frappe.safe_eval(doc.close_condition, None, {"workflow_state": done}), msg=done
			)

	def test_the_pro_holds_it_only_while_it_is_being_applied_for(self):
		doc = _rule("Work Permit-PRO")

		self.assertTrue(
			frappe.safe_eval(doc.assign_condition, None, {"workflow_state": "Apply Online by PRO"})
		)
		self.assertTrue(
			frappe.safe_eval(doc.unassign_condition, None, {"workflow_state": "Pending By Supervisor"})
		)

	def test_the_supervisor_is_assigned_while_a_transfer_waits_for_payment(self):
		"""The export spelt the state "Pending For Payment" with one space, which matches
		nothing - the supervisor would never have been assigned there."""
		doc = _rule("Work Permit - GRD Supervisor")

		self.assertTrue(
			frappe.safe_eval(doc.assign_condition, None, {"workflow_state": PAYMENT_STATE})
		)
		self.assertFalse(
			frappe.safe_eval(doc.unassign_condition, None, {"workflow_state": PAYMENT_STATE})
		)

	def test_the_operator_lets_go_once_the_transfer_reaches_payment(self):
		"""The supervisor takes over there, so the operator has to release it - through
		unassign_condition, which only touches its own assignment."""
		doc = _rule("Work Permit - GR Operator")

		self.assertTrue(
			frappe.safe_eval(doc.unassign_condition, None, {"workflow_state": PAYMENT_STATE})
		)

	def test_every_state_named_in_a_condition_is_one_the_workflow_has(self):
		"""What caught the one-space spelling, and what catches the next rename."""
		import re

		known = set(_states())
		for name, field, condition in self.conditions():
			for quoted in re.findall(r'"([^"]+)"', condition):
				self.assertIn(quoted, known, msg=f"{name}.{field}")


class TestSavingAPermitActuallyAssignsSomeone(FrappeTestCase):
	"""The rules only matter if the on_update hook reaches them, so this goes through a
	real save rather than calling apply_assign directly."""

	def setUp(self):
		self.name = frappe.db.get_value(
			"Work Permit", {"work_permit_type": "Local Transfer"}, "name", order_by="creation desc"
		)
		if not self.name:
			self.skipTest("no Local Transfer Work Permit on this instance")

		self.was = frappe.db.get_value(
			"Work Permit", self.name, ["workflow_state", "docstatus"], as_dict=True
		)
		self.addCleanup(
			frappe.db.set_value, "Work Permit", self.name, dict(self.was), update_modified=False
		)
		# Every day is an assignment day on these rules, but the flag keeps the test from
		# depending on which one it is run on.
		frappe.flags.assignment_day = "Monday"
		self.addCleanup(lambda: frappe.flags.pop("assignment_day", None))

	def assigned(self):
		return frappe.get_all(
			"ToDo",
			filters={"reference_type": "Work Permit", "reference_name": self.name, "status": "Open"},
			fields=["allocated_to", "assignment_rule"],
		)

	def save_in(self, state):
		frappe.db.set_value(
			"Work Permit", self.name, {"workflow_state": state, "docstatus": 0}, update_modified=False
		)
		doc = frappe.get_doc("Work Permit", self.name)
		doc.flags.ignore_permissions = True
		doc.save()

	def test_the_supervisor_gets_it_at_pending_by_supervisor(self):
		self.save_in("Pending By Supervisor")

		self.assertEqual(
			[a.assignment_rule for a in self.assigned()], ["Work Permit - GRD Supervisor"]
		)

	def test_the_supervisor_gets_it_again_while_it_waits_for_payment(self):
		"""The state whose spelling was wrong in the export."""
		self.save_in(PAYMENT_STATE)

		self.assertEqual(
			[a.assignment_rule for a in self.assigned()], ["Work Permit - GRD Supervisor"]
		)

	def test_nobody_holds_it_once_it_is_completed(self):
		self.save_in("Completed")

		self.assertEqual(self.assigned(), [])
