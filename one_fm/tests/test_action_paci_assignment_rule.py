# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002183: the Action PACI assignment rule, as the business analyst holds it.

The rule was "Based on Process Task" with no task linked. `AssignmentRule.apply` reads the
assignee off the task, so every PACI it fired on was assigned to nobody - no error, nothing
in the log. It takes the record's owner now, which is both what the analyst's copy says and
the only version of it that assigns anyone.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

RULE = "Action PACI"

ASSIGNS_AT = ("Draft", "Pending by GR Operator", "Pending Address Update", "Pending Photo Update")


def _rule():
	return frappe.get_doc("Assignment Rule", RULE)


def _states():
	return {state.state for state in frappe.get_doc("Workflow", "PACI").states}


class TestTheRuleTakesTheOwner(FrappeTestCase):
	def test_it_is_based_on_the_owner_field(self):
		doc = _rule()

		self.assertEqual(doc.rule, "Based on Field")
		self.assertEqual(doc.field, "owner")

	def test_it_is_enabled_and_on_paci(self):
		doc = _rule()

		self.assertFalse(doc.disabled)
		self.assertEqual(doc.document_type, "PACI")

	def test_it_no_longer_depends_on_a_process_task(self):
		"""The failure this fixes: a task-based rule with no task assigns nobody, silently."""
		doc = _rule()

		self.assertNotEqual(doc.rule, "Based on Process Task")


class TestTheConditionsAreUnchanged(FrappeTestCase):
	"""WI-002183 changes where the assignee comes from, not when the rule fires."""

	def test_it_fires_on_the_four_operator_states(self):
		condition = _rule().assign_condition
		for state in ASSIGNS_AT:
			with self.subTest(state=state):
				self.assertTrue(
					frappe.safe_eval(condition, None, {"workflow_state": state}), msg=state
				)

	def test_it_closes_once_the_civil_id_is_done(self):
		self.assertTrue(
			frappe.safe_eval(_rule().close_condition, None, {"workflow_state": "Completed"})
		)

	def test_no_condition_raises_on_any_state_a_paci_can_hold(self):
		"""assign_condition is safe_eval'd with the document's own dict as locals, and
		anything that raises is swallowed into a msgprint - leaving the rule silently dead."""
		doc = _rule()
		for field in ("assign_condition", "unassign_condition", "close_condition"):
			if not doc.get(field):
				continue
			for state in _states():
				try:
					frappe.safe_eval(doc.get(field), None, {"workflow_state": state})
				except Exception as e:
					self.fail(f"{RULE}.{field} on {state!r}: {type(e).__name__}: {e}")
