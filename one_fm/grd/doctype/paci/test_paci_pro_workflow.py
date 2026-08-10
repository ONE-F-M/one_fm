# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-001830: the PRO tier a New Application PACI opens in."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from one_fm.grd.doctype.paci.paci import NEW_APPLICATION, PENDING_PRO, create_PACI

EXPECTED_TRANSITIONS = (
	("Draft", "Save", "Pending PRO"),
	("Pending PRO", "Submit", "Pending by PACI"),
	("Pending by PACI", "Approve", "Completed"),
	("Pending by PACI", "Reject", "Rejected"),
)


def _an_active_employee():
	name = frappe.db.get_value(
		"Employee",
		{"status": "Active", "relieving_date": ["is", "not set"], "residency_expiry_date": ["is", "set"]},
		"name",
		order_by="creation asc",
	)
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return frappe.get_doc("Employee", name)


class TestPACIProWorkflow(FrappeTestCase):
	def setUp(self):
		self.employee = _an_active_employee()

	def test_a_new_application_opens_with_the_pro(self):
		create_PACI(self.employee, NEW_APPLICATION)

		paci = frappe.get_last_doc("PACI", filters={"employee": self.employee.name})
		self.assertEqual(paci.category, NEW_APPLICATION)
		self.assertEqual(paci.workflow_state, PENDING_PRO)

		# And it is on someone's desk: the state is written to the field directly, which
		# leaves the assignment rules unaware unless they are re-run.
		assigned_to = frappe.get_all(
			"ToDo",
			filters={"reference_type": "PACI", "reference_name": paci.name, "status": "Open"},
			pluck="allocated_to",
		)
		self.assertTrue(assigned_to, "the PACI was left in Pending PRO assigned to nobody")
		self.assertEqual(
			assigned_to,
			[
				frappe.db.get_value(
					"Process Task",
					frappe.db.get_value("Assignment Rule", "PACI-PRO", "custom_routine_task"),
					"employee_user",
				)
			],
		)

	def test_the_other_categories_still_open_in_draft(self):
		"""Only the overseas first application starts with the PRO."""
		for category in ("Renewal", "Transfer"):
			with self.subTest(category=category):
				create_PACI(self.employee, category)
				paci = frappe.get_last_doc("PACI", filters={"employee": self.employee.name})
				self.assertEqual(paci.category, category)
				self.assertNotEqual(paci.workflow_state, PENDING_PRO)

	def test_the_workflow_carries_the_pro_round_trip(self):
		workflow = frappe.get_doc("Workflow", "PACI")

		transitions = {
			(t.state, t.action, t.next_state): t.allowed for t in workflow.transitions
		}
		for transition in EXPECTED_TRANSITIONS:
			self.assertIn(transition, transitions)

		# The PRO tier is the PRO's to act on and to edit; the PACI round-trip is the
		# operator's.
		self.assertEqual(transitions[("Draft", "Save", "Pending PRO")], "PRO")
		self.assertEqual(transitions[("Pending PRO", "Submit", "Pending by PACI")], "PRO")

		states = {s.state: s for s in workflow.states}
		self.assertEqual(states[PENDING_PRO].allow_edit, "PRO")
		# A state cannot be linked without its master, and create_workflow_state cannot
		# create one without a style - which is how this silently failed the first time.
		self.assertTrue(frappe.db.exists("Workflow State", "Pending by PACI"))

	def test_the_pro_is_assigned_a_pending_pro_record(self):
		rule = frappe.get_doc("Assignment Rule", "PACI-PRO")

		self.assertFalse(rule.disabled)
		self.assertEqual(rule.rule, "Based on Process Task")
		self.assertEqual(rule.assign_condition, 'workflow_state == "Pending PRO"')
		# A rule of this kind picks its assignee off the task, so a missing task means it
		# silently assigns nobody.
		self.assertTrue(rule.custom_routine_task)
		self.assertTrue(
			frappe.db.get_value("Process Task", rule.custom_routine_task, "employee"),
			"the PACI Process Task has no employee to assign to",
		)

	def test_both_roles_can_edit_a_completed_paci(self):
		"""allow_edit holds one role per state row, so two roles on Completed means two
		rows for it - which is how the BA site grants it, and what Frappe reads:
		get_document_state_roles collects the allow_edit of every row matching the state.

		Treating that second row as a duplicate is what took the operator's edit rights
		away, and nothing in the states-and-transitions check noticed.
		"""
		workflow = frappe.get_doc("Workflow", "PACI")
		roles = {state.allow_edit for state in workflow.states if state.state == "Completed"}

		self.assertEqual(roles, {"System Manager", "Government Relations Operator"})

	def test_the_completed_rows_agree_on_everything_but_the_role(self):
		"""Two rows for one state must not disagree about what the state means."""
		workflow = frappe.get_doc("Workflow", "PACI")
		rows = [state for state in workflow.states if state.state == "Completed"]

		self.assertEqual(len(rows), 2)
		for field in ("doc_status", "update_field", "update_value"):
			self.assertEqual(
				len({row.get(field) for row in rows}), 1, msg=f"the rows differ on {field}"
			)

	def test_the_reference_number_is_on_the_form(self):
		field = frappe.get_meta("PACI").get_field("paci_reference_number")

		self.assertIsNotNone(field, "PACI has no PACI Reference Number field")
		self.assertFalse(field.hidden)
		# The PRO types the government portal's reference in, so it must not be read only.
		self.assertFalse(field.read_only)

	def test_completing_a_paci_updates_the_employee_civil_id_expiry(self):
		"""AC-3, checked on the method the workflow's Completed state runs."""
		expiry = add_days(nowdate(), 365)
		create_PACI(self.employee, NEW_APPLICATION)
		paci = frappe.get_last_doc("PACI", filters={"employee": self.employee.name})
		paci.db_set("new_civil_id_expiry_date", expiry, update_modified=False)

		paci.set_New_civil_id_Expiry_date_in_employee_doctype()

		self.assertEqual(
			str(frappe.db.get_value("Employee", self.employee.name, "civil_id_expiry_date")),
			expiry,
		)
