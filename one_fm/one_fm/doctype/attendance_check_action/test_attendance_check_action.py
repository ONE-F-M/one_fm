# Copyright (c) 2026, ONE FM and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate, nowdate

from one_fm.one_fm.doctype.attendance_check_action.attendance_check_action import (
	UNPURCHASED_MOBILE_PENALTY_CODE,
	UNPURCHASED_MOBILE_PENALTY_REMARKS,
	create_penalty_for_unpurchased_mobile,
)


class TestAttendanceCheckAction(FrappeTestCase):
	def _new(self, **kwargs):
		doc = frappe.new_doc("Attendance Check Action")
		doc.update(kwargs)
		return doc

	def test_grace_period_computes_deadline(self):
		# Grace Period -> Deadline Date (Start Date + Grace Period)
		doc = self._new(start_date="2026-01-01", grace_period=14)
		doc.set_grace_and_deadline()
		self.assertEqual(getdate(doc.deadline_date), getdate("2026-01-15"))

	def test_deadline_computes_grace(self):
		# Deadline Date -> Grace Period (Deadline Date - Start Date)
		doc = self._new(start_date="2026-01-01", deadline_date="2026-01-15")
		doc.set_grace_and_deadline()
		self.assertEqual(doc.grace_period, 14)

	def test_self_purchase_defaults_grace_to_14(self):
		doc = self._new(start_date="2026-01-01", purchasing_method="Self Purchase")
		doc.set_grace_and_deadline()
		self.assertEqual(doc.grace_period, 14)
		self.assertEqual(getdate(doc.deadline_date), getdate("2026-01-15"))

	def test_company_loan_defaults_grace_to_14(self):
		doc = self._new(start_date="2026-01-01", purchasing_method="Company Loan")
		doc.set_grace_and_deadline()
		self.assertEqual(doc.grace_period, 14)

	def test_explicit_grace_is_not_overridden_by_method(self):
		# A grace period already entered must be respected, not reset to 14.
		doc = self._new(start_date="2026-01-01", purchasing_method="Self Purchase", grace_period=7)
		doc.set_grace_and_deadline()
		self.assertEqual(doc.grace_period, 7)
		self.assertEqual(getdate(doc.deadline_date), getdate("2026-01-08"))

	def test_negative_grace_period_rejected(self):
		# Deadline before Start Date implies a negative grace period.
		doc = self._new(start_date="2026-01-15", deadline_date="2026-01-01")
		with self.assertRaises(frappe.ValidationError):
			doc.set_grace_and_deadline()

	def _get_employee(self):
		"""Return an existing Employee to attach actions to, cleared of any
		leftover Attendance Check Actions so each test starts from a clean slate."""
		employee = frappe.db.get_value("Employee", {"status": "Active"}, "name")
		if not employee:
			self.skipTest("No Employee available to run duplicate-prevention tests")

		for name in frappe.get_all(
			"Attendance Check Action", filters={"employee": employee}, pluck="name"
		):
			frappe.delete_doc("Attendance Check Action", name, force=True, ignore_permissions=True)

		return employee

	def _make_action(self, employee, start_date, status="Draft"):
		doc = self._new(employee=employee, start_date=start_date, action="Issue a New Mobile")
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)
		if doc.status != status:
			doc.db_set("status", status)
		return doc

	def test_blocks_duplicate_when_open_action_exists(self):
		# AC1: an open (not Closed) action blocks creating another for the same employee.
		employee = self._get_employee()
		self._make_action(employee, "2026-02-01", status="Draft")

		dup = self._new(employee=employee, start_date="2026-02-05", action="Issue a New Mobile")
		dup.flags.ignore_mandatory = True
		with self.assertRaises(frappe.ValidationError):
			dup.insert(ignore_permissions=True)

	def test_blocks_duplicate_when_purchased_action_exists(self):
		# A Purchased action with no deadline (deadline not yet passed) still blocks
		# a second overlapping action for the same employee.
		employee = self._get_employee()
		self._make_action(employee, "2026-02-01", status="Purchased")

		dup = self._new(employee=employee, start_date="2026-02-05", action="Issue a New Mobile")
		dup.flags.ignore_mandatory = True
		with self.assertRaises(frappe.ValidationError):
			dup.insert(ignore_permissions=True)

	def test_deadline_passed_releases_block_for_new_action(self):
		# Once an action's Deadline Date has passed, a genuinely new issue may
		# start its own action even though the previous one is not yet Closed.
		employee = self._get_employee()
		old = self._new(
			employee=employee,
			start_date="2020-01-01",
			deadline_date="2020-01-15",
			action="Issue a New Mobile",
		)
		old.flags.ignore_mandatory = True
		old.insert(ignore_permissions=True)

		new_action = self._new(
			employee=employee, start_date="2020-06-01", action="Issue a New Mobile"
		)
		new_action.flags.ignore_mandatory = True
		new_action.insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("Attendance Check Action", new_action.name))

	def test_deadline_breached_rejected_before_deadline(self):
		# AC3 guard: "Deadline Breached" cannot be set while still within the grace
		# window (deadline in the future).
		employee = self._get_employee()
		doc = self._new(
			employee=employee,
			start_date="2099-01-01",
			deadline_date="2099-01-15",
			action="Issue a New Mobile",
		)
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)

		doc.status = "Deadline Breached"
		doc.flags.ignore_mandatory = True
		with self.assertRaises(frappe.ValidationError):
			doc.save()

	def test_deadline_breached_allowed_after_deadline(self):
		# AC3: once the deadline has passed the breach status is accepted.
		employee = self._get_employee()
		doc = self._new(
			employee=employee,
			start_date="2020-01-01",
			deadline_date="2020-01-15",
			action="Issue a New Mobile",
		)
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)

		doc.status = "Deadline Breached"
		doc.flags.ignore_mandatory = True
		doc.save()
		self.assertEqual(
			frappe.db.get_value("Attendance Check Action", doc.name, "status"),
			"Deadline Breached",
		)

	def test_allows_new_action_when_previous_is_closed(self):
		# AC2: once the previous action is Closed a brand new lifecycle may start.
		employee = self._get_employee()
		self._make_action(employee, "2026-02-01", status="Closed")

		new_action = self._new(employee=employee, start_date="2026-02-05", action="Issue a New Mobile")
		new_action.flags.ignore_mandatory = True
		new_action.insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("Attendance Check Action", new_action.name))

	def _make_closed_unpurchased_action(self, employee):
		"""Create a Closed action with "Has not Purchased a New Mobile" ticked,
		mirroring the state the record is in when on_submit fires the penalty job."""
		doc = self._make_action(employee, "2026-03-01", status="Closed")
		doc.db_set("has_not_purchased_a_new_mobile", 1)
		return doc

	def test_penalty_created_for_unpurchased_mobile(self):
		# AC: closing an action with the checkbox ticked raises a penalty linked
		# to the employee and the originating action, with the mandated values.
		employee = self._get_employee()
		action = self._make_closed_unpurchased_action(employee)

		create_penalty_for_unpurchased_mobile(action.name)

		penalty_name = frappe.db.get_value(
			"Penalty And Investigation", {"attendance_check_action": action.name}, "name"
		)
		self.assertTrue(penalty_name, "Penalty was not created for the closed action")

		penalty = frappe.get_doc("Penalty And Investigation", penalty_name)
		self.assertEqual(penalty.employee, employee)
		self.assertEqual(penalty.applied_penalty_code, UNPURCHASED_MOBILE_PENALTY_CODE)
		self.assertEqual(getdate(penalty.incident_date), getdate(nowdate()))
		self.assertEqual(penalty.supervisor_remarks, frappe._(UNPURCHASED_MOBILE_PENALTY_REMARKS))
		self.assertEqual(penalty.attendance_check_action, action.name)

		# Location and Department are sourced from the employee master.
		emp = frappe.db.get_value("Employee", employee, ["site", "department"], as_dict=True)
		self.assertEqual(penalty.location, emp.site)
		self.assertEqual(penalty.department, emp.department)

		# Issuer resolves the HR Settings action User to its Employee record.
		action_user = frappe.db.get_single_value("HR Settings", "attendance_check_action_user")
		expected_issuer = (
			frappe.db.get_value("Employee", {"user_id": action_user}, "name") if action_user else None
		)
		self.assertEqual(penalty.issuer, expected_issuer)

	def test_no_penalty_when_checkbox_unchecked(self):
		# A Closed action without the checkbox ticked must not raise a penalty.
		employee = self._get_employee()
		action = self._make_action(employee, "2026-03-01", status="Closed")

		create_penalty_for_unpurchased_mobile(action.name)

		self.assertFalse(
			frappe.db.exists("Penalty And Investigation", {"attendance_check_action": action.name})
		)

	def test_penalty_creation_is_idempotent(self):
		# Re-running the job for the same action must not create a duplicate penalty.
		employee = self._get_employee()
		action = self._make_closed_unpurchased_action(employee)

		create_penalty_for_unpurchased_mobile(action.name)
		create_penalty_for_unpurchased_mobile(action.name)

		self.assertEqual(
			frappe.db.count("Penalty And Investigation", {"attendance_check_action": action.name}),
			1,
		)
