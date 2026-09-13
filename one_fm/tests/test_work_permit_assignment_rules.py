# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-001827: the three Work Permit assignment rules the work item links to.

WI-002182 brought them back to the configuration the business analyst holds: the GR Manager
rule covers one state rather than two, the GR Operator rule is back on the owner, and the
PRO rule is off. A fourth rule, "Work Permit Completion - GR Operator", is gone - it
assigned on a state the workflow has no transition into, so it never fired.
"""

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
	# WI-002182: one state. Pending  For Payment is a state the supervisor moves a permit
	# out of, not one it waits in.
	"Work Permit - GR Manager": {
		"assign_condition": 'workflow_state in ["Pending GR Manager"]',
		"unassign_condition": 'workflow_state not in ["Pending GR Manager"]',
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


# WI-002182: the PRO rule is off. A disabled rule here is part of the configuration, not a
# rule that failed to apply.
DISABLED = {"Work Permit-PRO"}

# WI-002182: the rule that no longer exists. It assigned on "Pending Expiry Date Update",
# which the Work Permit workflow has no transition into.
REMOVED_RULE = "Work Permit Completion - GR Operator"


class TestTheRulesExist(FrappeTestCase):
	def test_all_three_are_there(self):
		for rule in RULES:
			doc = _rule(rule["name"])

			self.assertEqual(doc.document_type, "Work Permit", msg=rule["name"])
			self.assertEqual(bool(doc.disabled), rule["name"] in DISABLED, msg=rule["name"])

	def test_the_rule_that_never_fired_is_gone(self):
		self.assertFalse(frappe.db.exists("Assignment Rule", REMOVED_RULE))

	def test_no_other_rule_assigns_work_permits(self):
		"""Two rules for one state split the queue in half and nobody notices."""
		self.assertEqual(
			sorted(frappe.get_all(
				"Assignment Rule", filters={"document_type": "Work Permit"}, pluck="name"
			)),
			sorted(rule["name"] for rule in RULES),
		)

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

	def test_a_task_based_rule_has_a_task_that_names_somebody(self):
		"""An unlinked "Based on Process Task" rule assigns nobody, and says nothing."""
		for rule in RULES:
			doc = _rule(rule["name"])
			if doc.rule != "Based on Process Task":
				continue

			self.assertTrue(doc.custom_routine_task, msg=rule["name"])
			self.assertTrue(
				frappe.db.get_value("Process Task", doc.custom_routine_task, "employee_user"),
				msg=f"{rule['name']}: task has no user to assign",
			)

	def test_the_operator_keeps_the_permit_they_raised(self):
		"""WI-002182: back on the owner. A task would send every permit to one person,
		whoever raised it."""
		doc = _rule("Work Permit - GR Operator")

		self.assertEqual(doc.rule, "Based on Field")
		self.assertEqual(doc.field, "owner")

	def test_no_two_rules_share_a_task(self):
		task_based = [
			_rule(rule["name"]) for rule in RULES
			if _rule(rule["name"]).rule == "Based on Process Task"
		]
		linked = {doc.custom_routine_task for doc in task_based}

		self.assertEqual(len(linked), len(task_based))


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
			frappe.safe_eval(doc.unassign_condition, None, {"workflow_state": "Pending GR Manager"})
		)

	def test_the_gr_manager_holds_it_only_at_its_own_state(self):
		"""WI-002182: not through Pending  For Payment - the supervisor moves a permit out
		of that state rather than waiting in it."""
		doc = _rule("Work Permit - GR Manager")

		self.assertTrue(
			frappe.safe_eval(doc.assign_condition, None, {"workflow_state": "Pending GR Manager"})
		)
		self.assertFalse(
			frappe.safe_eval(doc.assign_condition, None, {"workflow_state": PAYMENT_STATE})
		)
		self.assertTrue(
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

	def test_the_gr_manager_gets_it_at_pending_gr_manager(self):
		self.save_in("Pending GR Manager")

		self.assertEqual(
			[a.assignment_rule for a in self.assigned()], ["Work Permit - GR Manager"]
		)

	def test_nobody_is_assigned_while_it_waits_for_payment(self):
		"""WI-002182: the GR Manager rule no longer covers that state, and the operator
		releases it there. The permit waits on a payment, not on a person."""
		self.save_in(PAYMENT_STATE)

		self.assertEqual([a.assignment_rule for a in self.assigned()], [])

	def test_nobody_holds_it_once_it_is_completed(self):
		self.save_in("Completed")

		self.assertEqual(self.assigned(), [])
