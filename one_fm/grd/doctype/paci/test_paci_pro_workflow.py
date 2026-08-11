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

	def test_the_rejection_reason_dropdown_offers_what_ba_supplied(self):
		"""AC3: the pop-up on Reject prompts for a reason, and it has to be a value the
		field will accept on save - so the dialog reads its options off the field."""
		field = frappe.get_meta("PACI").get_field("paci_rejection_reason")

		self.assertIsNotNone(field)
		self.assertEqual(field.options.split("\n"), ["", "Incorrect Address", "Incorrect Data"])
		# Rejected is a draft state, but Completed is submitted - a reason recorded on a
		# submitted record needs this.
		self.assertTrue(field.allow_on_submit)

	def test_the_reject_dialog_is_wired_to_the_rejecting_state(self):
		source = frappe.read_file(
			frappe.get_app_path("one_fm", "grd", "doctype", "paci", "paci.js")
		)

		self.assertIn("before_workflow_action", source)
		self.assertIn("Pending by PACI", source)
		# Options off the field, not a list kept in the client.
		self.assertIn("frappe.meta.get_docfield('PACI', 'paci_rejection_reason'", source)

	def test_the_state_the_dialog_fires_from_can_actually_reject(self):
		"""A dialog on an action the workflow does not offer would never open."""
		transitions = {
			(t.state, t.action, t.next_state)
			for t in frappe.get_doc("Workflow", "PACI").transitions
		}

		self.assertIn(("Pending by PACI", "Reject", "Rejected"), transitions)

	def test_only_a_rejected_paci_can_be_reapplied(self):
		from one_fm.grd.doctype.paci.paci import can_reapply

		self.assertTrue(can_reapply(frappe._dict(workflow_state="Rejected")))
		for state in ("Draft", "Pending PRO", "Pending by PACI", "Completed"):
			self.assertFalse(can_reapply(frappe._dict(workflow_state=state)), msg=state)

	def test_the_reapply_link_field_points_back_and_is_not_copied_onward(self):
		"""AC4's parent reference link. no_copy so a copy of a copy does not inherit it."""
		field = frappe.get_meta("PACI").get_field("rejected_paci")

		self.assertIsNotNone(field)
		self.assertEqual(field.options, "PACI")
		self.assertTrue(field.read_only)
		self.assertTrue(field.no_copy)

	def test_reapplying_clears_the_reference_and_keeps_the_candidate(self):
		from one_fm.grd.doctype.paci.paci import reapply_paci

		employee = frappe.db.get_value(
			"Employee", {"status": "Active", "relieving_date": ["is", "not set"]}, "name"
		)
		source = frappe.get_doc(
			{
				"doctype": "PACI",
				"employee": employee,
				"category": "New Application",
				"date_of_application": frappe.utils.today(),
			}
		).insert(ignore_permissions=True)
		frappe.db.set_value(
			"PACI",
			source.name,
			{
				"workflow_state": "Rejected",
				"paci_reference_number": "PACI-REF-999",
				"paci_rejection_reason": "Incorrect Address",
			},
			update_modified=False,
		)
		self.addCleanup(
			lambda: frappe.db.delete("PACI", {"rejected_paci": source.name})
		)

		new = frappe.get_doc("PACI", reapply_paci(source.name)["name"])

		self.assertEqual(new.rejected_paci, source.name)
		self.assertEqual(new.workflow_state, "Draft")
		self.assertEqual(new.employee, source.employee)
		self.assertEqual(new.category, source.category)
		self.assertFalse(new.paci_reference_number)
		self.assertFalse(new.paci_rejection_reason)

		# The rejected one is the history and stays as it is.
		self.assertEqual(
			frappe.db.get_value("PACI", source.name, "paci_rejection_reason"), "Incorrect Address"
		)

	def test_completing_writes_the_expiry_without_validating_the_whole_employee(self):
		"""AC5 broke on data that has nothing to do with a civil ID: 1,124 employees hold
		a Marital Status the field's options no longer accept ("Single", "Divorced",
		"Widowed"), and employee.save() validates all of it. The two facts this has - the
		document row and the expiry date - are written directly instead."""
		employee = frappe.db.get_value(
			"Employee",
			{
				"marital_status": ["not in", (frappe.get_meta("Employee").get_field("marital_status").options or "").split("\n")],
				"status": "Active",
				"work_permit_expiry_date": ["is", "set"],
			},
			"name",
		)
		if not employee:
			self.skipTest("no employee with an out-of-options Marital Status on this instance")

		expiry = frappe.db.get_value("Employee", employee, "work_permit_expiry_date")
		frappe.db.delete("Employee Document", {"parent": employee, "document_name": "Civil ID"})

		paci = frappe.get_doc(
			{
				"doctype": "PACI",
				"employee": employee,
				"category": "New Application",
				"date_of_application": frappe.utils.today(),
				"upload_civil_id": "/files/civil-id.pdf",
			}
		).insert(ignore_permissions=True)

		# Would raise ValidationError on the employee's Marital Status before this.
		paci.set_New_civil_id_Expiry_date_in_employee_doctype()

		self.assertEqual(
			frappe.db.get_value("Employee", employee, "civil_id_expiry_date"), expiry
		)
		rows = frappe.db.get_all(
			"Employee Document",
			{"parent": employee, "document_name": "Civil ID"},
			["idx", "valid_till"],
		)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].valid_till, expiry)
		# A raw insert gets no ordering for free, so idx has to be worked out.
		self.assertGreaterEqual(rows[0].idx, 1)

	def test_a_second_document_row_does_not_tie_on_idx(self):
		from one_fm.grd.doctype.paci.paci import next_employee_document_idx

		employee = frappe.db.get_value("Employee", {"status": "Active"}, "name")
		highest = frappe.db.get_value(
			"Employee Document",
			{"parent": employee, "parenttype": "Employee"},
			"idx",
			order_by="idx desc",
		)

		self.assertEqual(next_employee_document_idx(employee), (highest or 0) + 1)

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
