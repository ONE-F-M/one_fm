# -*- coding: utf-8 -*-
# Copyright (c) 2026, ONE-F-M and Contributors
# See license.txt
import frappe
import unittest
from frappe.utils import today, add_days, now_datetime

from one_fm.overrides.employee import NOT_RETURNED_FROM_LEAVE


class TestBlockCheckinNotReturnedFromLeave(unittest.TestCase):
	"""Tests for blocking Employee Checkin when an employee has not returned from leave."""

	def setUp(self):
		frappe.flags.in_test = 1
		frappe.set_user("Administrator")
		frappe.flags.in_import = True
		frappe.flags.ignore_permissions = True

		self.company = frappe.db.get_value("Company", {"is_group": 0}, "name") or "Test Company"
		self.employee = self._create_test_employee("Active")
		frappe.db.commit()

	def tearDown(self):
		# Clean up test checkins
		frappe.db.sql(
			"DELETE FROM `tabEmployee Checkin` WHERE employee = %s",
			self.employee.name,
		)
		frappe.delete_doc("Employee", self.employee.name, force=1, ignore_permissions=True)
		frappe.db.commit()

	def _create_test_employee(self, status):
		"""Create a minimal test employee with the given status."""
		employee = frappe.get_doc({
			"doctype": "Employee",
			"first_name": "Checkin Block Test",
			"employee_name": "Checkin Block Test",
			"one_fm_first_name_in_arabic": "اختبار",
			"one_fm_last_name_in_arabic": "حظر",
			"status": status,
			"date_of_birth": "1990-01-01",
			"date_of_joining": add_days(today(), -365),
			"gender": "Male",
			"company": self.company,
			"one_fm_basic_salary": 100,
			"day_off_category": "Weekly",
			"number_of_days_off": 1,
			"create_user_permission": 0,
		}).insert(ignore_permissions=True)
		return employee

	def test_checkin_blocked_for_not_returned_from_leave(self):
		"""An employee who has not returned from leave must NOT be able to check in."""
		frappe.db.set_value("Employee", self.employee.name, "status", NOT_RETURNED_FROM_LEAVE)
		frappe.db.commit()
		frappe.clear_cache(doctype="Employee")

		checkin = frappe.new_doc("Employee Checkin")
		checkin.employee = self.employee.name
		checkin.log_type = "IN"
		checkin.time = now_datetime()

		self.assertRaises(frappe.ValidationError, checkin.insert)

	def test_checkin_allowed_for_active_employee(self):
		"""Employee with status 'Active' should be able to check in."""
		checkin = frappe.new_doc("Employee Checkin")
		checkin.employee = self.employee.name
		checkin.log_type = "IN"
		checkin.time = now_datetime()

		# Should not raise — insert succeeds
		try:
			checkin.insert(ignore_permissions=True)
		except frappe.ValidationError as e:
			if "Access Denied" in str(e):
				self.fail("Active employee was incorrectly blocked from checking in.")

	def test_checkin_allowed_after_status_restored(self):
		"""After status changes back to 'Active', checkin should succeed."""
		# Block first
		frappe.db.set_value("Employee", self.employee.name, "status", NOT_RETURNED_FROM_LEAVE)
		frappe.db.commit()
		frappe.clear_cache(doctype="Employee")

		checkin = frappe.new_doc("Employee Checkin")
		checkin.employee = self.employee.name
		checkin.log_type = "IN"
		checkin.time = now_datetime()

		self.assertRaises(frappe.ValidationError, checkin.insert)

		# Restore status
		frappe.db.set_value("Employee", self.employee.name, "status", "Active")
		frappe.db.commit()
		frappe.clear_cache(doctype="Employee")

		# Should succeed now
		checkin2 = frappe.new_doc("Employee Checkin")
		checkin2.employee = self.employee.name
		checkin2.log_type = "IN"
		checkin2.time = now_datetime()

		try:
			checkin2.insert(ignore_permissions=True)
		except frappe.ValidationError as e:
			if "Access Denied" in str(e):
				self.fail("Employee was still blocked after status was restored to Active.")

	def test_blocked_checkin_error_message(self):
		"""Verify the exact error message text for blocked checkin."""
		frappe.db.set_value("Employee", self.employee.name, "status", NOT_RETURNED_FROM_LEAVE)
		frappe.db.commit()
		frappe.clear_cache(doctype="Employee")

		checkin = frappe.new_doc("Employee Checkin")
		checkin.employee = self.employee.name
		checkin.log_type = "IN"
		checkin.time = now_datetime()

		with self.assertRaises(frappe.ValidationError) as ctx:
			checkin.insert()

		self.assertIn("Duty Resumption", str(ctx.exception))
		self.assertIn("Access Denied", str(ctx.exception))
