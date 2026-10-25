# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt

from contextlib import ExitStack
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, now, today

from one_fm.one_fm.doctype.client_interview_shortlist.client_interview_shortlist import (
	send_pending_operations_supervisor_reminder,
)


class TestClientInterviewShortlist(FrappeTestCase):
	def test_project_required_without_prospective_client(self):
		shortlist = make_client_interview_shortlist(project=None)
		self.assertRaises(frappe.ValidationError, shortlist.validate)

	def test_prospective_client_required_when_flagged(self):
		shortlist = make_client_interview_shortlist(is_prospective_client=1, prospective_client=None)
		self.assertRaises(frappe.ValidationError, shortlist.validate)

	def test_prospective_client_clears_project(self):
		shortlist = make_client_interview_shortlist(
			project="Any Project", is_prospective_client=1, prospective_client="Any Opportunity"
		)
		shortlist.validate()
		self.assertIsNone(shortlist.project)

	def test_project_clears_prospective_client(self):
		shortlist = make_client_interview_shortlist(
			project="Any Project", prospective_client="Any Opportunity", customer_name="Any Customer"
		)
		shortlist.validate()
		self.assertIsNone(shortlist.prospective_client)
		self.assertIsNone(shortlist.customer_name)


class TestClientInterviewShortlistProcessaHandover(FrappeTestCase):
	def test_assignment_rules_are_removed(self):
		from one_fm.patches.v15_0.remove_client_interview_shortlist_assignment_rules import (
			ASSIGNMENT_RULES,
			execute,
		)

		execute()
		execute()
		for rule in ASSIGNMENT_RULES:
			self.assertFalse(frappe.db.exists("Assignment Rule", rule))
		self.assertFalse(
			frappe.db.exists(
				"Process Task",
				{
					"erp_document": "Client Interview Shortlist",
					"task": "Review and Approve Client Interview Shortlist",
					"is_active": 1,
				},
			)
		)

	def test_frappe_workflow_is_inactive(self):
		from frappe.model.workflow import get_workflow_name

		from one_fm.patches.v15_0.deactivate_client_interview_shortlist_workflow import execute

		execute()
		execute()
		self.assertFalse(get_workflow_name("Client Interview Shortlist"))


SHORTLIST = "Client Interview Shortlist"


def make_role(role):
	if not frappe.db.exists("Role", role):
		frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)


def make_user(email, roles):
	if frappe.db.exists("User", email):
		frappe.delete_doc("User", email, force=True, ignore_permissions=True)
	for role in roles:
		make_role(role)
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": email.split("@")[0],
			"send_welcome_email": 0,
			"roles": [{"role": role} for role in roles],
		}
	)
	user.insert(ignore_permissions=True)
	return user.name


def insert_raw_shortlist(owner, docstatus, **extra):
	"""Insert a shortlist straight into the database (no hooks, workflow or BPMN start)."""
	name = "TEST-CIS-" + frappe.generate_hash(length=8)
	doc = frappe.get_doc(
		{
			"doctype": SHORTLIST,
			"name": name,
			"owner": owner,
			"creation": extra.pop("creation", now()),
			"modified": now(),
			"modified_by": owner,
			"docstatus": docstatus,
			"interview_date": add_days(today(), 1),
		}
	)
	doc.db_insert()
	if extra:
		frappe.db.set_value(SHORTLIST, name, extra, update_modified=False)
	return name


class TestClientInterviewAttendancePermission(FrappeTestCase):
	"""The narrow Attendance escalation for the Client Interview Shortlist flow."""

	def setUp(self):
		self.addCleanup(frappe.set_user, "Administrator")
		self._user_contexts = ExitStack()
		self.addCleanup(self._user_contexts.close)
		frappe.set_user("Administrator")
		self.supervisor = make_user("cis_ops_supervisor@example.com", ["Operations Supervisor"])
		self.stranger = make_user("cis_stranger@example.com", ["Employee"])
		self.hr_manager = make_user("cis_hr_manager@example.com", ["HR Manager"])
		self.submitted = insert_raw_shortlist(owner="Administrator", docstatus=1)
		self.draft = insert_raw_shortlist(owner="Administrator", docstatus=0)

	def _attendance(self, **kwargs):
		values = {
			"doctype": "Attendance",
			"status": "Client Interview",
			"attendance_date": add_days(today(), -1),
			"reference_doctype": SHORTLIST,
			"reference_docname": self.submitted,
		}
		values.update(kwargs)
		return frappe.get_doc(values)

	def _assert_denied(self, user, permtype="create", **kwargs):
		self.set_user(user)
		doc = self._attendance(**kwargs)
		self.assertRaises(frappe.PermissionError, doc.check_permission, permtype)

	def _employee(self):
		employee = frappe.db.get_value(
			"Employee",
			{"status": "Active", "date_of_joining": ["<=", add_days(today(), -60)]},
			["name", "employee_name", "company", "department"],
			as_dict=True,
		)
		if not employee:
			self.skipTest("no active Employee available for an end-to-end Attendance")
		return employee

	def test_ops_supervisor_can_create_and_submit_attendance(self):
		employee = self._employee()
		date = add_days(today(), -2)
		values = {
			"employee": employee.name,
			"employee_name": employee.employee_name,
			"company": employee.company,
			"department": employee.department,
			"attendance_date": date,
		}
		frappe.db.delete("Attendance", {"employee": employee.name, "attendance_date": date})
		self.set_user(self.supervisor)

		# Before: the same user without the Client Interview Shortlist reference is refused.
		with self.assertRaises(frappe.PermissionError):
			self._attendance(reference_doctype=None, reference_docname=None, **values).insert()

		# After: with the reference to a submitted shortlist, create and submit both succeed.
		attendance = self._attendance(**values)
		attendance.insert()
		attendance.submit()
		self.assertEqual(frappe.db.get_value("Attendance", attendance.name, "docstatus"), 1)

	def test_check_permission_covers_create_write_submit(self):
		self.set_user(self.supervisor)
		doc = self._attendance()
		for permtype in ("create", "write", "submit"):
			doc.check_permission(permtype)
		# Anything else still goes through the normal permission check.
		self.assertRaises(frappe.PermissionError, doc.check_permission, "cancel")
		self.assertRaises(frappe.PermissionError, doc.check_permission, "delete")

	def test_operations_manager_is_allowed(self):
		manager = make_user("cis_ops_manager@example.com", ["Operations Manager"])
		self.set_user(manager)
		self._attendance(status="Absent").check_permission("create")

	def test_shortlist_owner_without_operations_role_is_allowed(self):
		owned = insert_raw_shortlist(owner=self.stranger, docstatus=1)
		self.set_user(self.stranger)
		self._attendance(reference_docname=owned).check_permission("create")

	def test_missing_or_other_reference_doctype_is_denied(self):
		self._assert_denied(self.supervisor, reference_doctype=None, reference_docname=None)
		self._assert_denied(self.supervisor, reference_doctype="", reference_docname=self.submitted)
		self._assert_denied(
			self.supervisor, reference_doctype="Attendance Request", reference_docname=self.submitted
		)
		self._assert_denied(self.supervisor, reference_docname=None)

	def test_unsubmitted_or_missing_shortlist_is_denied(self):
		self._assert_denied(self.supervisor, reference_docname=self.draft)
		self._assert_denied(self.supervisor, reference_docname="TEST-CIS-DOES-NOT-EXIST")

	def test_other_status_is_denied(self):
		self._assert_denied(self.supervisor, status="Present", working_hours=8)
		self._assert_denied(self.supervisor, permtype="submit", status="Present", working_hours=8)

	def test_unrelated_user_is_denied(self):
		self._assert_denied(self.stranger)
		self._assert_denied(self.stranger, permtype="submit")

	def set_user(self, user):
		"""Switch the session user for the rest of the test.

		FrappeTestCase.set_user is a context manager in Frappe v15, so it is entered here and
		kept open until the test ends; if it were a plain method the call itself switches user.
		"""
		context = super().set_user(user)
		if hasattr(context, "__enter__"):
			self._user_contexts.enter_context(context)
		else:
			frappe.set_user(user)

	def test_normal_permissions_are_unaffected(self):
		# HR Manager keeps normal create rights on a plain Attendance.
		self.set_user(self.hr_manager)
		self._attendance(reference_doctype=None, reference_docname=None, status="Present").check_permission(
			"create"
		)
		# A plain Employee is still denied on a plain Attendance.
		self._assert_denied(
			self.stranger, reference_doctype=None, reference_docname=None, status="Present"
		)


class TestPendingOperationsSupervisorReminder(FrappeTestCase):
	def setUp(self):
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		self.creator = make_user("cis_reminder_creator@example.com", ["Operations Supervisor"])
		self.old = add_days(today(), -3)

	def _pending(self, docstatus):
		return insert_raw_shortlist(
			owner=self.creator,
			docstatus=docstatus,
			creation=self.old,
			workflow_state="Pending Operations Supervisor",
		)

	def _reminded(self):
		with patch("frappe.sendmail") as sendmail:
			send_pending_operations_supervisor_reminder()
		return " ".join(call.kwargs.get("subject", "") for call in sendmail.call_args_list)

	def test_submitted_shortlist_is_excluded_and_pending_draft_is_included(self):
		draft = self._pending(0)
		submitted = self._pending(1)
		subjects = self._reminded()
		self.assertIn(draft, subjects)
		self.assertNotIn(submitted, subjects)

	def test_draft_with_errored_process_instance_is_skipped(self):
		draft = self._pending(0)
		instance = frappe.get_doc(
			{
				"doctype": "BPMN Process Instance",
				"name": "TEST-BPI-" + frappe.generate_hash(length=8),
				"context_doctype": SHORTLIST,
				"context_docname": draft,
				"status": "Errored",
				"owner": "Administrator",
				"creation": now(),
				"modified": now(),
				"modified_by": "Administrator",
			}
		)
		instance.db_insert()
		self.assertNotIn(draft, self._reminded())


def make_client_interview_shortlist(**kwargs):
	return frappe.get_doc(
		{
			"doctype": "Client Interview Shortlist",
			"interview_date": add_days(today(), 1),
			"client_interview_employee": [],
			**kwargs,
		}
	)
