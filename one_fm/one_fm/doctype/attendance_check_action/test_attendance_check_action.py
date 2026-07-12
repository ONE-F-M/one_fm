# Copyright (c) 2026, ONE FM and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate


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
		# "Purchased" is also NOT Closed, so it must block too.
		employee = self._get_employee()
		self._make_action(employee, "2026-02-01", status="Purchased")

		dup = self._new(employee=employee, start_date="2026-02-05", action="Issue a New Mobile")
		dup.flags.ignore_mandatory = True
		with self.assertRaises(frappe.ValidationError):
			dup.insert(ignore_permissions=True)

	def test_allows_new_action_when_previous_is_closed(self):
		# AC2: once the previous action is Closed a brand new lifecycle may start.
		employee = self._get_employee()
		self._make_action(employee, "2026-02-01", status="Closed")

		new_action = self._new(employee=employee, start_date="2026-02-05", action="Issue a New Mobile")
		new_action.flags.ignore_mandatory = True
		new_action.insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("Attendance Check Action", new_action.name))
