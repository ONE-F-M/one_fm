# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.overrides.attendance_request import get_permission_query_conditions


def create_employee(first_name, email, reports_to=None, department=None):
	"""Create (or fetch) a User + Employee, optionally reporting to another Employee."""
	if not frappe.db.exists("User", email):
		frappe.get_doc({
			"doctype": "User",
			"email": email,
			"first_name": first_name,
			"send_welcome_email": 0,
			"roles": [{"doctype": "Has Role", "role": "Employee"}],
		}).insert(ignore_permissions=True)

	existing = frappe.db.get_value("Employee", {"user_id": email}, "name")
	if existing:
		return existing

	company = frappe.db.get_value("Company", {}, "name") or "_Test Company"
	if not department:
		department = frappe.db.get_value("Department", {"company": company}, "name") \
			or frappe.db.get_value("Department", {}, "name")

	employee = frappe.get_doc({
		"doctype": "Employee",
		"first_name": first_name,
		"last_name": "Test",
		"company": company,
		"user_id": email,
		"date_of_birth": "1990-05-08",
		"date_of_joining": "2013-01-01",
		"department": department,
		"gender": "Male",
		"status": "Active",
		"reports_to": reports_to,
		"one_fm_first_name_in_arabic": "اختبار",
		"one_fm_last_name_in_arabic": "الموظف",
		"one_fm_basic_salary": 1000,
	}).insert(ignore_permissions=True)
	return employee.name


class TestAttendanceRequestPermission(FrappeTestCase):
	"""
		Validates the Attendance Request list permission filter that limits visibility to
		the current user's own requests plus those of their direct and indirect reports.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# Reporting chain: manager <- supervisor <- employee
		cls.manager = create_employee("AR Perm Manager", "ar_perm_manager@example.com")
		cls.supervisor = create_employee(
			"AR Perm Supervisor", "ar_perm_supervisor@example.com", reports_to=cls.manager
		)
		cls.employee = create_employee(
			"AR Perm Employee", "ar_perm_employee@example.com", reports_to=cls.supervisor
		)

		# A separate reporting line (different department head): other_manager <- other_employee
		cls.other_manager = create_employee("AR Perm Other Mgr", "ar_perm_other_mgr@example.com")
		cls.other_employee = create_employee(
			"AR Perm Other Emp", "ar_perm_other_emp@example.com", reports_to=cls.other_manager
		)

	def test_direct_report_visible(self):
		"""AC1: a manager can see a direct report's request."""
		condition = get_permission_query_conditions("ar_perm_supervisor@example.com")
		self.assertIn(self.employee, condition)

	def test_indirect_report_visible_down_the_chain(self):
		"""AC2: a higher-level manager can see reports down the whole reporting chain."""
		condition = get_permission_query_conditions("ar_perm_manager@example.com")
		# Direct report (supervisor) and indirect report (employee) both visible
		self.assertIn(self.supervisor, condition)
		self.assertIn(self.employee, condition)

	def test_own_record_visible(self):
		"""Scope decision: manager also sees their own requests."""
		condition = get_permission_query_conditions("ar_perm_manager@example.com")
		self.assertIn(self.manager, condition)

	def test_other_reporting_line_hidden(self):
		"""AC3: a manager from another line must not see an unrelated employee's request."""
		condition = get_permission_query_conditions("ar_perm_other_mgr@example.com")
		self.assertIn(self.other_employee, condition)
		# Employees from the first reporting line must be absent
		self.assertNotIn(self.employee, condition)
		self.assertNotIn(self.supervisor, condition)

	def test_condition_targets_employee_column(self):
		"""AC4: the filter is a real query condition on the employee column (hides in search/list)."""
		condition = get_permission_query_conditions("ar_perm_manager@example.com")
		self.assertIn("`tabAttendance Request`.`employee` in (", condition)

	def test_system_manager_bypass(self):
		"""System Manager gets full visibility (empty condition)."""
		self.assertEqual(get_permission_query_conditions("Administrator"), "")

		frappe.get_doc("User", "ar_perm_manager@example.com").add_roles("System Manager")
		self.addCleanup(
			frappe.get_doc("User", "ar_perm_manager@example.com").remove_roles, "System Manager"
		)
		self.assertEqual(get_permission_query_conditions("ar_perm_manager@example.com"), "")

	def test_user_without_employee_sees_nothing(self):
		"""A non-employee, non-privileged user is restricted to no records."""
		email = "ar_perm_no_employee@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc({
				"doctype": "User",
				"email": email,
				"first_name": "AR Perm No Emp",
				"send_welcome_email": 0,
				"roles": [{"doctype": "Has Role", "role": "Employee"}],
			}).insert(ignore_permissions=True)
		self.assertEqual(get_permission_query_conditions(email), "1=0")
