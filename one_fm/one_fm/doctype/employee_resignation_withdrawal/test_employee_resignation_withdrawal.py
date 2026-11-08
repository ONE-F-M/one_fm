# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from contextlib import contextmanager
from unittest.mock import patch

from frappe.model.document import Document
from frappe.model.workflow import apply_workflow
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.doctype.employee_resignation_withdrawal.employee_resignation_withdrawal import (
	set_rejection_reason,
)

class TestEmployeeResignationWithdrawal(FrappeTestCase):
	def setUp(self):
		# Reaching the first approval step notifies the Offboarding Officers, which
		# needs an outgoing Email Account the test site has no reason to configure.
		frappe.flags.mute_emails = True
		self.addCleanup(lambda: frappe.flags.update({"mute_emails": False}))

		emp_name = _make_employee("test_erw_employee@example.com", "Test ERW Employee")
		self.employee = frappe.get_doc("Employee", emp_name)
		
		# Create an Employee Resignation
		self.resignation = frappe.get_doc({
			"doctype": "Employee Resignation",
			"employee": self.employee.name,
			"resignation_initiation_date": frappe.utils.today(),
			"reason_for_exit": "Better opportunity",
			"resignation_letter": "/files/resignation_letter.txt",
			"status": "Pending",
			"relieving_date": frappe.utils.add_days(frappe.utils.today(), 30)
		}).insert()
		
	def tearDown(self):
		frappe.db.rollback()

	def test_validate_rejection_reason_missing(self):
		erw = frappe.get_doc({
			"doctype": "Employee Resignation Withdrawal",
			"employee_resignation": self.resignation.name,
			"reason": "Test",
			"resignation_withdrawal_letter": "/files/test.txt"
		}).insert()
		_submit_for_review(erw)

		# Change state without giving reason
		erw.workflow_state = "Rejected"

		with self.assertRaises(frappe.ValidationError) as context:
			erw.save()

		self.assertTrue("Please provide Reason for Rejection" in str(context.exception))

	def test_validate_rejection_reason_provided(self):
		erw = frappe.get_doc({
			"doctype": "Employee Resignation Withdrawal",
			"employee_resignation": self.resignation.name,
			"reason": "Test",
			"resignation_withdrawal_letter": "/files/test.txt"
		}).insert()
		_submit_for_review(erw)

		# Change state and provide reason
		erw.workflow_state = "Rejected"
		erw.reason_for_rejection = "Not a valid reason"

		# Should not raise any error
		erw.save()
		self.assertEqual(erw.workflow_state, "Rejected")

	def test_reject_through_the_workflow_without_a_stored_reason_is_blocked(self):
		# apply_workflow() reloads the document from the database, so a reason that
		# only exists on the approver's form never reaches validate_rejection_reason().
		erw = self._withdrawal_awaiting_project_manager()
		erw.reason_for_rejection = "Rejected -- wrong procedure"

		with self.assertRaises(frappe.ValidationError) as context:
			apply_workflow(erw, "Reject")

		self.assertTrue("Please provide Reason for Rejection" in str(context.exception))
		# Not asserting the stored workflow_state here: the throw happens in
		# on_update, after the row has already been written, and it is the
		# request-level rollback -- absent inside a test transaction -- that undoes
		# it. The refusal is the contract worth pinning.

	def test_reject_through_the_workflow_once_the_reason_is_stored(self):
		erw = self._withdrawal_awaiting_project_manager()
		set_rejection_reason(erw.name, "  Rejected -- wrong procedure  ")

		apply_workflow(erw, "Reject")

		erw.reload()
		self.assertEqual(erw.workflow_state, "Rejected")
		# Stored whitespace-trimmed, and survives the reload apply_workflow performs.
		self.assertEqual(erw.reason_for_rejection, "Rejected -- wrong procedure")

	def test_set_rejection_reason_refuses_an_empty_reason(self):
		erw = self._withdrawal_awaiting_project_manager()

		with self.assertRaises(frappe.ValidationError) as context:
			set_rejection_reason(erw.name, "   ")

		self.assertTrue("Please provide Reason for Rejection" in str(context.exception))

	def test_set_rejection_reason_refuses_a_withdrawal_not_awaiting_approval(self):
		erw = self._withdrawal_awaiting_project_manager()
		set_rejection_reason(erw.name, "Rejected -- wrong procedure")
		apply_workflow(erw, "Reject")

		with self.assertRaises(frappe.ValidationError) as context:
			set_rejection_reason(erw.name, "Changed my mind")

		self.assertTrue("awaiting approval" in str(context.exception))

	def test_set_rejection_reason_refuses_anyone_but_the_current_approver(self):
		# Pending Supervisor allows edit by "Employee" -- the role every requester
		# holds -- so neither the DocType permissions nor the workflow state stop
		# an employee from reaching this method on their own withdrawal. The
		# approver check is the only thing that does.
		#
		# check_permission is stubbed out so the assertion is about our gate and
		# not about frappe's permission stack, which rejects any throwaway test
		# user long before the gate is reached.
		erw = self._withdrawal_awaiting_supervisor()
		erw.db_set("supervisor", "test_erw_approver@example.com")

		with self._acting_as("test_erw_requester@example.com"):
			with self.assertRaises(frappe.PermissionError):
				set_rejection_reason(erw.name, "Rejected -- wrong procedure")

		self.assertIsNone(
			frappe.db.get_value("Employee Resignation Withdrawal", erw.name, "reason_for_rejection")
		)

	def test_set_rejection_reason_allows_the_current_approver(self):
		erw = self._withdrawal_awaiting_supervisor()
		erw.db_set("supervisor", "test_erw_approver@example.com")

		with self._acting_as("test_erw_approver@example.com"):
			set_rejection_reason(erw.name, "Rejected -- wrong procedure")

		self.assertEqual(
			frappe.db.get_value("Employee Resignation Withdrawal", erw.name, "reason_for_rejection"),
			"Rejected -- wrong procedure",
		)

	def test_set_rejection_reason_checks_the_approver_for_the_state_it_is_in(self):
		# The supervisor signs off at the first step but has no say once the
		# withdrawal has moved on to the Project Manager.
		erw = self._withdrawal_awaiting_project_manager()
		erw.db_set("supervisor", "test_erw_supervisor@example.com")
		erw.db_set("project_manager", "test_erw_approver@example.com")

		with self._acting_as("test_erw_supervisor@example.com"):
			with self.assertRaises(frappe.PermissionError):
				set_rejection_reason(erw.name, "Rejected -- wrong procedure")

		with self._acting_as("test_erw_approver@example.com"):
			set_rejection_reason(erw.name, "Rejected -- wrong procedure")

		self.assertEqual(
			frappe.db.get_value("Employee Resignation Withdrawal", erw.name, "reason_for_rejection"),
			"Rejected -- wrong procedure",
		)

	@contextmanager
	def _acting_as(self, user, roles=("Employee",)):
		"""Run as a user holding only the given roles, with the DocType
		permission check stubbed out. Granting a real desk role is not an option
		here: User.after_insert forces a role profile on any user linked to an
		Employee, and the next save repopulates roles from it."""
		with patch.object(Document, "check_permission", return_value=None):
			with patch.object(frappe, "get_roles", return_value=list(roles)):
				original = frappe.session.user
				frappe.session.user = user
				try:
					yield
				finally:
					frappe.session.user = original

	def test_rejecting_through_the_transition_still_checks_the_approver(self):
		# one_fm.overrides.workflow.apply_workflow saves the payload the browser
		# sends without reloading it, so a reason can reach the server without
		# going through set_rejection_reason. The document has to hold the line.
		erw = self._withdrawal_awaiting_supervisor()
		# A real save validates links, so the approver has to exist.
		erw.db_set("supervisor", _make_user("test_erw_approver@example.com"))

		erw.reload()
		erw.workflow_state = "Rejected"
		erw.reason_for_rejection = "Rejected -- wrong procedure"

		with self._acting_as("test_erw_requester@example.com"):
			with self.assertRaises(frappe.PermissionError):
				erw.save()
		# As with the missing-reason case, the stored state is not asserted: the
		# check runs in on_update, after the write, and the request-level
		# rollback is what undoes it.

	def test_approving_does_not_require_a_reason_for_rejection(self):
		erw = self._withdrawal_awaiting_project_manager()

		apply_workflow(erw, "Approve")

		self.assertEqual(
			frappe.db.get_value("Employee Resignation Withdrawal", erw.name, "workflow_state"),
			"Approved",
		)

	def _withdrawal_awaiting_supervisor(self):
		"""A saved withdrawal on the first approval step, the one state the
		workflow leaves open to the "Employee" role at large."""
		erw = frappe.get_doc({
			"doctype": "Employee Resignation Withdrawal",
			"employee_resignation": self.resignation.name,
			"reason": "Test",
			"resignation_withdrawal_letter": "/files/test.txt"
		}).insert()
		_submit_for_review(erw)
		return erw

	def _withdrawal_awaiting_project_manager(self):
		"""A saved withdrawal sitting on the Project Manager step, which is the
		branch Ali Alazmi could not reject and the only Reject transition that
		carries no routing condition."""
		erw = frappe.get_doc({
			"doctype": "Employee Resignation Withdrawal",
			"employee_resignation": self.resignation.name,
			"reason": "Test",
			"resignation_withdrawal_letter": "/files/test.txt"
		}).insert()
		_submit_for_review(erw)

		erw.workflow_state = "Pending Project Manager"
		if not erw.offboarding_officer:
			erw.offboarding_officer = "Administrator"
		erw.save()
		return erw

	def test_process_withdrawal_approval(self):
		# Create a PMR tied to the resignation if the doctype exists
		pmr = None
		if frappe.db.exists("DocType", "Project Manpower Request"):
			pmr = frappe.get_doc({
				"doctype": "Project Manpower Request",
				"employee_resignation": self.resignation.name,
				"project": _get_or_create_project("Test ERW Project", self.employee.company),
				"title": "Test PMR"
			}).insert(ignore_mandatory=True)

		# Set an initial relieving date on the employee to verify it gets cleared
		frappe.db.set_value("Employee", self.employee.name, "relieving_date", frappe.utils.today())

		erw = frappe.get_doc({
			"doctype": "Employee Resignation Withdrawal",
			"employee_resignation": self.resignation.name,
			"reason": "Changed my mind",
			"resignation_withdrawal_letter": "/files/test.txt"
		}).insert()
		_submit_for_review(erw)

		# Operations branch: Supervisor forwards straight to Project Manager, no
		# separate "Accepted by Supervisor" state anymore.
		erw.workflow_state = "Pending Project Manager"
		erw.save()

		# Trigger withdrawal approval
		erw.workflow_state = "Approved"
		erw.save()

		# Assertions
		self.employee.reload()
		self.resignation.reload()

		self.assertEqual(self.resignation.status, "Withdrawn")
		if frappe.db.has_column("Employee Resignation", "workflow_state"):
			self.assertEqual(self.resignation.workflow_state, "Withdrawn")
		
		self.assertIsNone(self.employee.relieving_date)
		
		if pmr:
			pmr.reload()
			self.assertEqual(pmr.status, "Withdrawn")
			if frappe.db.has_column("Project Manpower Request", "workflow_state"):
				self.assertEqual(pmr.workflow_state, "Withdrawn")

	def test_withdrawing_a_resignation_still_under_review_closes_its_tasks(self):
		from frappe.desk.form.assign_to import add as add_assignment

		reviewer = _make_user("test_erw_pending_reviewer@example.com")
		add_assignment(
			{"assign_to": [reviewer], "doctype": "Employee Resignation", "name": self.resignation.name}
		)

		erw = frappe.get_doc(
			{
				"doctype": "Employee Resignation Withdrawal",
				"employee_resignation": self.resignation.name,
				"reason": "Changed my mind before approval",
				"resignation_withdrawal_letter": "/files/test.txt",
			}
		).insert()
		_submit_for_review(erw)
		erw.workflow_state = "Pending Project Manager"
		erw.save()
		erw.workflow_state = "Approved"
		erw.save()

		self.assertEqual(frappe.db.get_value("Employee Resignation", self.resignation.name, "workflow_state"), "Withdrawn")
		self.assertFalse(
			frappe.db.exists(
				"ToDo",
				{"reference_type": "Employee Resignation", "reference_name": self.resignation.name, "status": "Open"},
			)
		)

	def test_approval_withdraws_pmr_waiting_for_recruiter(self):
		pmr = frappe.get_doc({
			"doctype": "Project Manpower Request",
			"employee_resignation": self.resignation.name,
			"reason": "Exit",
			"count": 1,
			"project_allocation": self.employee.project,
			"designation": self.employee.designation,
			"title": "Test PMR Awaiting Recruiter",
		}).insert()
		pmr.workflow_state = "Awaiting Recruiter Approval"
		pmr.save()
		frappe.db.set_value("Employee", self.employee.name, "relieving_date", frappe.utils.today())

		erw = frappe.get_doc({
			"doctype": "Employee Resignation Withdrawal",
			"employee_resignation": self.resignation.name,
			"reason": "Changed my mind",
			"resignation_withdrawal_letter": "/files/test.txt",
		}).insert()
		_submit_for_review(erw)
		erw.workflow_state = "Pending Project Manager"
		erw.save()
		erw.workflow_state = "Approved"
		erw.save()

		pmr.reload()
		self.assertEqual(pmr.workflow_state, "Withdrawn")
		withdrawn_qty = sum(row.qty for row in pmr.fulfillment_actions if row.action_type == "Resignation Withdrawal")
		self.assertEqual(withdrawn_qty, 1)
		self.assertEqual(frappe.db.get_value("Employee Resignation", self.resignation.name, "workflow_state"), "Withdrawn")
		self.assertIsNone(frappe.db.get_value("Employee", self.employee.name, "relieving_date"))

	def test_withdrawal_blocked_when_pmr_completed(self):
		if frappe.db.exists("DocType", "Project Manpower Request"):
			pmr = frappe.get_doc({
				"doctype": "Project Manpower Request",
				"employee_resignation": self.resignation.name,
				"project": _get_or_create_project("Test ERW Project", self.employee.company),
				"title": "Test PMR"
			}).insert(ignore_mandatory=True)
			# Set directly rather than via save(): a new PMR's workflow_state must
			# start at that workflow's states[0], same constraint as Withdrawal's
			# own workflow -- bypass to simulate an already-completed PMR.
			pmr.db_set("workflow_state", "Completed", update_modified=False)

			erw = frappe.get_doc({
				"doctype": "Employee Resignation Withdrawal",
				"employee_resignation": self.resignation.name,
				"reason": "Changed my mind",
				"resignation_withdrawal_letter": "/files/test.txt",
			})

			with self.assertRaises(frappe.ValidationError) as context:
				erw.validate()

			self.assertTrue("Cannot withdraw resignation because the replacement Project Manpower Request" in str(context.exception))

	def test_blocks_second_active_withdrawal(self):
		frappe.get_doc({
			"doctype": "Employee Resignation Withdrawal",
			"employee_resignation": self.resignation.name,
			"reason": "Changed my mind",
			"resignation_withdrawal_letter": "/files/test.txt",
		}).insert()

		second = frappe.get_doc({
			"doctype": "Employee Resignation Withdrawal",
			"employee_resignation": self.resignation.name,
			"reason": "Changed my mind again",
			"resignation_withdrawal_letter": "/files/test2.txt",
		})

		with self.assertRaises(frappe.ValidationError) as context:
			second.insert()

		self.assertTrue("still in progress" in str(context.exception))

	def test_allows_new_withdrawal_after_previous_resolved(self):
		first = frappe.get_doc({
			"doctype": "Employee Resignation Withdrawal",
			"employee_resignation": self.resignation.name,
			"reason": "Changed my mind",
			"resignation_withdrawal_letter": "/files/test.txt",
		}).insert()

		_submit_for_review(first)
		first.workflow_state = "Rejected"
		first.reason_for_rejection = "Not accepted"
		first.save()

		second = frappe.get_doc({
			"doctype": "Employee Resignation Withdrawal",
			"employee_resignation": self.resignation.name,
			"reason": "Trying again",
			"resignation_withdrawal_letter": "/files/test2.txt",
		}).insert()

		self.assertEqual(second.employee, self.employee.name)


	def test_insert_lands_on_draft_without_reason_or_letter(self):
		erw = frappe.get_doc({
			"doctype": "Employee Resignation Withdrawal",
			"employee_resignation": self.resignation.name,
		}).insert()

		self.assertEqual(erw.workflow_state, "Draft")
		self.assertFalse(erw.reason)
		self.assertFalse(erw.resignation_withdrawal_letter)

	def test_submit_for_review_requires_reason_and_letter(self):
		erw = frappe.get_doc({
			"doctype": "Employee Resignation Withdrawal",
			"employee_resignation": self.resignation.name,
		}).insert()

		erw.workflow_state = "Pending Supervisor"
		with self.assertRaises(frappe.ValidationError) as context:
			erw.save()

		self.assertTrue("Reason and a Withdrawal Letter" in str(context.exception))


	def test_approvers_follow_the_employee_current_record(self):
		stale_user = _make_user("test_erw_stale_supervisor@example.com")
		frappe.db.set_value("Employee Resignation", self.resignation.name, {
			"supervisor": stale_user,
			"project_manager": stale_user,
		})

		new_supervisor = _make_employee_with_user("test_erw_new_supervisor@example.com", "Test ERW New Supervisor")
		new_pm = _make_employee_with_user("test_erw_new_pm@example.com", "Test ERW New PM")
		frappe.db.set_value("Employee", self.employee.name, "reports_to", new_supervisor)
		frappe.db.set_value("Project", self.employee.project, "project_manager", new_pm)

		erw = frappe.get_doc({
			"doctype": "Employee Resignation Withdrawal",
			"employee_resignation": self.resignation.name,
			"reason": "Changed my mind",
		}).insert()

		self.assertEqual(erw.supervisor, "test_erw_new_supervisor@example.com")
		self.assertEqual(erw.project_manager, "test_erw_new_pm@example.com")


	def test_daily_hand_over_moves_the_pending_step_to_the_current_supervisor(self):
		from frappe.desk.form.assign_to import add
		from one_fm.one_fm.doctype.employee_resignation.employee_resignation import hand_over_in_process_approvals

		erw = frappe.get_doc({
			"doctype": "Employee Resignation Withdrawal",
			"employee_resignation": self.resignation.name,
			"reason": "Changed my mind",
			"resignation_withdrawal_letter": "/files/test.txt",
		}).insert()
		_submit_for_review(erw)

		stale_user = _make_user("test_erw_old_supervisor@example.com")
		erw.db_set("supervisor", stale_user)
		add({"assign_to": [stale_user], "doctype": erw.doctype, "name": erw.name, "description": "Approve"})

		new_supervisor = _make_employee_with_user("test_erw_moved_supervisor@example.com", "Test ERW Moved Supervisor")
		frappe.db.set_value("Employee", self.employee.name, "reports_to", new_supervisor)

		hand_over_in_process_approvals()

		self.assertEqual(frappe.db.get_value(erw.doctype, erw.name, "supervisor"), "test_erw_moved_supervisor@example.com")
		open_todos = frappe.get_all("ToDo", filters={
			"reference_type": erw.doctype, "reference_name": erw.name, "status": "Open",
		}, pluck="allocated_to")
		self.assertIn("test_erw_moved_supervisor@example.com", open_todos)
		self.assertNotIn(stale_user, open_todos)

	def test_approvers_fall_back_to_the_resignation_when_none_is_current(self):
		resignation_user = _make_user("test_erw_resignation_approver@example.com")
		frappe.db.set_value("Employee Resignation", self.resignation.name, {
			"supervisor": resignation_user,
			"project_manager": resignation_user,
		})
		frappe.db.set_value("Employee", self.employee.name, {"reports_to": None, "site": None})
		frappe.db.set_value("Project", self.employee.project, "project_manager", None)

		erw = frappe.get_doc({
			"doctype": "Employee Resignation Withdrawal",
			"employee_resignation": self.resignation.name,
			"reason": "Changed my mind",
		}).insert()

		self.assertEqual(erw.supervisor, resignation_user)
		self.assertEqual(erw.project_manager, resignation_user)

	def test_a_closed_withdrawal_keeps_the_approvers_who_acted_on_it(self):
		erw = frappe.get_doc({
			"doctype": "Employee Resignation Withdrawal",
			"employee_resignation": self.resignation.name,
			"reason": "Changed my mind",
			"resignation_withdrawal_letter": "/files/test.txt",
		}).insert()
		approver = _make_user("test_erw_old_supervisor@example.com")
		erw.db_set({"supervisor": approver, "workflow_state": "Rejected", "reason_for_rejection": "No"})
		new_supervisor = _make_employee_with_user("test_erw_moved_supervisor@example.com", "Test ERW Moved Supervisor")
		frappe.db.set_value("Employee", self.employee.name, "reports_to", new_supervisor)

		erw.reload()
		erw.save()

		self.assertEqual(erw.supervisor, approver)

	def test_daily_hand_over_assigns_the_new_supervisor_when_the_old_one_had_no_task(self):
		from one_fm.one_fm.doctype.employee_resignation.employee_resignation import hand_over_in_process_approvals

		erw = frappe.get_doc({
			"doctype": "Employee Resignation Withdrawal",
			"employee_resignation": self.resignation.name,
			"reason": "Changed my mind",
			"resignation_withdrawal_letter": "/files/test.txt",
		}).insert()
		_submit_for_review(erw)
		erw.db_set("supervisor", _make_user("test_erw_old_supervisor@example.com"))
		frappe.db.set_value(
			"ToDo", {"reference_type": erw.doctype, "reference_name": erw.name}, "status", "Closed"
		)
		new_supervisor = _make_employee_with_user("test_erw_moved_supervisor@example.com", "Test ERW Moved Supervisor")
		frappe.db.set_value("Employee", self.employee.name, "reports_to", new_supervisor)

		hand_over_in_process_approvals()

		self.assertTrue(frappe.db.exists("ToDo", {
			"reference_type": erw.doctype, "reference_name": erw.name,
			"allocated_to": "test_erw_moved_supervisor@example.com", "status": "Open",
		}))

	def test_daily_hand_over_continues_past_a_record_that_fails(self):
		from unittest.mock import patch

		from one_fm.one_fm.doctype.employee_resignation import employee_resignation

		other_employee = _make_employee("test_erw_other_employee@example.com", "Test ERW Other Employee")
		other_resignation = frappe.get_doc({
			"doctype": "Employee Resignation",
			"employee": other_employee,
			"resignation_initiation_date": frappe.utils.today(),
			"reason_for_exit": "Better opportunity",
			"resignation_letter": "/files/resignation_letter.txt",
			"relieving_date": frappe.utils.add_days(frappe.utils.today(), 30),
		}).insert()
		withdrawals = []
		for resignation in (self.resignation.name, other_resignation.name):
			erw = frappe.get_doc({
				"doctype": "Employee Resignation Withdrawal",
				"employee_resignation": resignation,
				"reason": "Changed my mind",
				"resignation_withdrawal_letter": "/files/test.txt",
			}).insert()
			_submit_for_review(erw)
			erw.db_set("supervisor", _make_user("test_erw_old_supervisor@example.com"))
			withdrawals.append(erw)
		broken, working = withdrawals
		new_supervisor = _make_employee_with_user("test_erw_moved_supervisor@example.com", "Test ERW Moved Supervisor")
		for employee in (self.employee.name, other_employee):
			frappe.db.set_value("Employee", employee, "reports_to", new_supervisor)

		real_hand_over = employee_resignation.hand_over_approval

		def fail_on_broken(doc):
			if doc.name == broken.name:
				doc.db_set("supervisor", "test_erw_moved_supervisor@example.com")
				raise frappe.PermissionError("Missing Permission")
			real_hand_over(doc)

		with patch.object(employee_resignation, "hand_over_approval", side_effect=fail_on_broken):
			employee_resignation.hand_over_in_process_approvals()

		self.assertEqual(frappe.db.get_value(broken.doctype, broken.name, "supervisor"), "test_erw_old_supervisor@example.com")
		self.assertEqual(frappe.db.get_value(working.doctype, working.name, "supervisor"), "test_erw_moved_supervisor@example.com")
		self.assertTrue(frappe.db.exists("Error Log", {"reference_name": broken.name}))

	def test_daily_hand_over_skips_withdrawals_not_in_process(self):
		from one_fm.one_fm.doctype.employee_resignation.employee_resignation import hand_over_in_process_approvals

		erw = frappe.get_doc({
			"doctype": "Employee Resignation Withdrawal",
			"employee_resignation": self.resignation.name,
			"reason": "Changed my mind",
		}).insert()
		stale_user = _make_user("test_erw_old_supervisor@example.com")
		erw.db_set("supervisor", stale_user)
		new_supervisor = _make_employee_with_user("test_erw_moved_supervisor@example.com", "Test ERW Moved Supervisor")
		frappe.db.set_value("Employee", self.employee.name, "reports_to", new_supervisor)

		hand_over_in_process_approvals()

		self.assertEqual(frappe.db.get_value(erw.doctype, erw.name, "supervisor"), stale_user)


def _make_user(email):
	if not frappe.db.exists("User", email):
		# User creation is capped at 60 an hour per site, and a suite that is run
		# repeatedly burns through that; in_import is the only exemption.
		in_import = frappe.flags.in_import
		frappe.flags.in_import = True
		try:
			frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}).insert()
		finally:
			frappe.flags.in_import = in_import
	return email


def _make_employee_with_user(email, employee_name):
	emp_name = _make_employee(email, employee_name)
	frappe.db.set_value("Employee", emp_name, "user_id", _make_user(email))
	return emp_name


def _submit_for_review(erw):
	# Test employees are all non-corporate / Operations-branch, so the entry
	# state Draft resolves to is always "Pending Supervisor".
	erw.workflow_state = "Pending Supervisor"
	erw.save()


def _make_employee(employee_id, employee_name):
	company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.get_all("Company", limit=1)[0].name
	existing = frappe.db.get_value("Employee", {"employee": employee_id})
	if not existing:
		doc = frappe.get_doc({
			"doctype": "Employee",
			"employee": employee_id,
			"employee_name": employee_name,
			"first_name": employee_name,
			"last_name": "Test",
			"one_fm_first_name_in_arabic": "تست",
			"one_fm_last_name_in_arabic": "تست",
			"gender": "Male",
			"date_of_birth": "1990-01-01",
			"company": company,
			"department": _get_or_create_department("Test Department", company),
			"one_fm_basic_salary": 1000,
			"date_of_joining": frappe.utils.add_days(frappe.utils.today(), -100),
			"status": "Active",
			"project": _get_or_create_project("Test ERW Project", company),
			"designation": _get_or_create_designation("Test ERW Designation")
		}).insert()
		return doc.name
	return existing

def _get_or_create_project(project_name, company):
	if not frappe.db.exists("Project", project_name):
		frappe.get_doc({
			"doctype": "Project",
			"project_name": project_name,
			"company": company
		}).insert()
	return project_name

def _get_or_create_designation(designation_name):
	if not frappe.db.exists("Designation", designation_name):
		frappe.get_doc({
			"doctype": "Designation",
			"designation_name": designation_name
		}).insert()
	return designation_name

def _get_or_create_department(department_name, company):
	# The actual name in DB is usually 'Department Name - Company Abbr'
	# To make it simple, let's just create a unique one or get it if exists
	company_abbr = frappe.get_cached_value('Company', company, 'abbr') or company
	full_dept_name = f"{department_name} - {company_abbr}"
	
	if not frappe.db.exists("Department", full_dept_name):
		frappe.get_doc({
			"doctype": "Department",
			"department_name": department_name,
			"department_code": "TEST-DEPT",
			"company": company
		}).insert()
	return full_dept_name
