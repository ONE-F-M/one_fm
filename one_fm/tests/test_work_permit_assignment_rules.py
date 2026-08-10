# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-001827: the three Work Permit assignment rules the work item links to."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0.add_work_permit_assignment_rules import RULES

PAYMENT_STATE = "Pending  For Payment"  # two spaces, as the workflow spells it

# Transcribed from the export the work item links to. These pin the rules against drift:
# what is applied has to match, field for field.
EXPORTED = {
	"Work Permit-PRO": {
		"assign_condition": 'workflow_state == "Apply Online by PRO"',
		"close_condition": 'workflow_state != "Apply Online by PRO"',
	},
	"Work Permit - GRD Supervisor": {
		"assign_condition": 'doc.workflow_state in ["Pending By Supervisor", "Pending For Payment"]',
		"close_condition": 'doc.workflow_state not in ["Pending By Supervisor", "Pending For Payment"]',
	},
	"Work Permit - GR Operator": {
		"assign_condition": (
			'workflow_state in ["Apply Online by PRO", "Pending By PAM", '
			'"Pending By Previous Company", "Pending By Operator", "Reason of Rejection"]'
		),
		"close_condition": (
			'workflow_state in ["Pending By Supervisor", "Pending For Payment", '
			'"Completed", "Rejected"]'
		),
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
				self.assertEqual(doc.get(field), expected, msg=f"{name}.{field}")

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


class TestWhatTheExportedConditionsDo(FrappeTestCase):
	"""assign_condition is eval'd as safe_eval(condition, None, doc.as_dict()) - the
	document's own fields are the locals. Two of the exported conditions do not work under
	that, and these tests record which, so the day either is corrected on the BA side the
	failure says exactly what changed."""

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
			frappe.safe_eval(doc.close_condition, None, {"workflow_state": "Pending By Supervisor"})
		)

	def test_the_supervisor_rule_cannot_evaluate_at_all(self):
		"""KNOWN, as exported: `doc` is not a name in scope, so the rule never assigns and
		every Work Permit save shows "Auto assignment failed: name 'doc' is not defined".
		Dropping the `doc.` prefix is the whole fix - awaiting the BA's word."""
		doc = _rule("Work Permit - GRD Supervisor")

		with self.assertRaises(NameError):
			frappe.safe_eval(doc.assign_condition, None, {"workflow_state": "Pending By Supervisor"})

	def test_no_rule_matches_the_payment_state(self):
		"""KNOWN, as exported: the conditions spell it "Pending For Payment" with one
		space, so nothing matches the real state and nobody is assigned while a transfer
		waits for payment. Adding the second space is the whole fix."""
		for name in ("Work Permit-PRO", "Work Permit - GR Operator"):
			self.assertFalse(
				frappe.safe_eval(
					_rule(name).assign_condition, None, {"workflow_state": PAYMENT_STATE}
				),
				msg=name,
			)

		self.assertNotIn(PAYMENT_STATE, _rule("Work Permit - GRD Supervisor").assign_condition)

	def test_the_payment_state_is_spelt_with_two_spaces(self):
		"""What makes the one above a defect rather than a preference."""
		self.assertIn(PAYMENT_STATE, _states())
		self.assertNotIn("Pending For Payment", _states())
