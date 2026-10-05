# Copyright (c) 2022, ONE FM and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from one_fm.operations.doctype.roster_day_off_checker.roster_day_off_checker import (
	calculate_expected_days_off,
	get_take_action_data,
	is_exit_before_month_midpoint,
)

MODULE = "one_fm.operations.doctype.roster_day_off_checker.roster_day_off_checker"


class StubChecker(frappe._dict):
	"""Stand-in for the checker document.

	A module-level class rather than a _dict carrying a lambda: Frappe pickles values it
	caches, and a locally defined lambda cannot be pickled.
	"""

	def check_permission(self, *args, **kwargs):
		return None


class TestRosterDayOffChecker(FrappeTestCase):
	def test_standard_month_before_midpoint_forces_zero(self):
		# Final working date before the 15th of a standard month -> expected days off 0
		relieving_date = getdate("2026-07-10")
		self.assertTrue(is_exit_before_month_midpoint(relieving_date, relieving_date))

	def test_standard_month_day_before_cutoff_forces_zero(self):
		# The 14th is still before the 15th cutoff for standard months
		relieving_date = getdate("2026-07-14")
		self.assertTrue(is_exit_before_month_midpoint(relieving_date, relieving_date))

	def test_standard_month_on_cutoff_uses_existing_calculation(self):
		# The 15th is the cutoff (inclusive) -> existing proportional calculation applies
		relieving_date = getdate("2026-07-15")
		self.assertFalse(is_exit_before_month_midpoint(relieving_date, relieving_date))

	def test_standard_month_after_cutoff_uses_existing_calculation(self):
		relieving_date = getdate("2026-07-20")
		self.assertFalse(is_exit_before_month_midpoint(relieving_date, relieving_date))

	def test_february_before_midpoint_forces_zero(self):
		# February final working date before the 14th -> expected days off 0
		relieving_date = getdate("2026-02-13")
		self.assertTrue(is_exit_before_month_midpoint(relieving_date, relieving_date))

	def test_february_on_cutoff_uses_existing_calculation(self):
		# The 14th is the February cutoff (inclusive) -> existing calculation applies
		relieving_date = getdate("2026-02-14")
		self.assertFalse(is_exit_before_month_midpoint(relieving_date, relieving_date))

	def test_february_after_cutoff_uses_existing_calculation(self):
		relieving_date = getdate("2026-02-20")
		self.assertFalse(is_exit_before_month_midpoint(relieving_date, relieving_date))

	def test_leap_year_february_uses_fourteenth_cutoff(self):
		# February always uses the 14th cutoff, including leap years (2024 has 29 days)
		self.assertTrue(is_exit_before_month_midpoint(getdate("2024-02-13"), getdate("2024-02-13")))
		self.assertFalse(is_exit_before_month_midpoint(getdate("2024-02-14"), getdate("2024-02-14")))

	def test_no_relieving_date_uses_existing_calculation(self):
		# Non-exiting employee (no relieving date) -> rule never applies
		self.assertFalse(is_exit_before_month_midpoint(getdate("2026-07-10"), None))

	def test_period_end_not_clamped_to_exit_uses_existing_calculation(self):
		# When the period end is not the employee's final working day (e.g. exit falls in a
		# later month, so the period end is the month-end), the rule must not fire even
		# though the relieving day is before a midpoint.
		period_end = getdate("2026-07-31")
		relieving_date = getdate("2026-08-10")
		self.assertFalse(is_exit_before_month_midpoint(period_end, relieving_date))

	def test_accepts_string_dates(self):
		# Values may arrive as strings from SQL/UI; the helper normalises via getdate
		self.assertTrue(is_exit_before_month_midpoint("2026-07-10", "2026-07-10"))
		self.assertFalse(is_exit_before_month_midpoint("2026-07-31", "2026-08-10"))


class TestCalculateExpectedDaysOff(FrappeTestCase):
	def test_fully_suspended_month_forces_zero(self):
		# AC1: employee suspended every day of a 30-day month -> 0 applicable days -> 0 days off
		self.assertEqual(calculate_expected_days_off(0, 30, 4), 0)

	def test_fully_suspended_week_forces_zero(self):
		# AC1: employee suspended every day of the week -> 0 applicable days -> 0 days off
		self.assertEqual(calculate_expected_days_off(0, 7, 1), 0)

	def test_monthly_no_deductions_returns_full_entitlement(self):
		# No suspended/leave days -> applicable days == days in month -> full entitlement
		self.assertEqual(calculate_expected_days_off(30, 30, 4), 4)

	def test_monthly_partial_suspension_subtracts_days(self):
		# AC2/AC3 Monthly: 30-day month, 4 days off/month, 15 suspended days.
		# Applicable = 30 - 15 = 15 -> 15 / 30 * 4 = 2
		self.assertEqual(calculate_expected_days_off(15, 30, 4), 2)

	def test_weekly_no_deductions_returns_full_entitlement(self):
		# 7-day week, 1 day off/week, no deductions -> full entitlement
		self.assertEqual(calculate_expected_days_off(7, 7, 1), 1)

	def test_weekly_partial_suspension_subtracts_days(self):
		# AC2/AC3 Weekly: 7-day week, 2 days off/week, 3 suspended days.
		# Applicable = 7 - 3 = 4 -> 4 / 7 * 2
		self.assertAlmostEqual(calculate_expected_days_off(4, 7, 2), 4 / 7 * 2)

	def test_zero_total_days_returns_zero(self):
		# Guard against division by zero when the comparison period collapses to nothing
		self.assertEqual(calculate_expected_days_off(0, 0, 4), 0)

	def test_rounding_behaviour_matches_caller(self):
		# The caller rounds the result; here we confirm the raw proportional value so the
		# rounding contract (round() applied in add_period) stays explicit.
		# 20 applicable / 30 days * 4 = 2.666...
		self.assertAlmostEqual(calculate_expected_days_off(20, 30, 4), 20 / 30 * 4)
		self.assertEqual(round(calculate_expected_days_off(20, 30, 4)), 3)



class TestTakeActionData(FrappeTestCase):
	"""
	WI-001654: Take Action opens the roster pre-filtered by employee, project, site, shift
	and role. The checker document and Employee lookup are stubbed so the filter
	resolution is tested without Employee/Operations fixtures.
	"""

	def _checker(self, **overrides):
		doc = StubChecker(
			{
				"name": "OPR-RDOC-TEST",
				"employee": "EMP-TEST-0001",
				"employee_id": "EMPID-1",
				"employee_name": "Test Worker",
				"project_allocation": "Project A",
				"site_allocation": "Site A",
				"shift_allocation": "Shift A",
				"date": "2026-07-11",
			}
		)
		doc.update(overrides)
		return doc

	def _employee(self, **overrides):
		employee = frappe._dict(
			{
				"project": "Employee Project",
				"site": "Employee Site",
				"shift": "Employee Shift",
				"custom_operations_role_allocation": "Role A",
				"employee_id": "EMPID-FALLBACK",
				"employee_name": "Fallback Name",
			}
		)
		employee.update(overrides)
		return employee

	def _run(self, checker=None, employee="default"):
		employee_value = self._employee() if employee == "default" else employee
		with patch(f"{MODULE}.frappe.get_doc", return_value=checker or self._checker()):
			with patch(f"{MODULE}.frappe.db.get_value", return_value=employee_value):
				return get_take_action_data("OPR-RDOC-TEST")

	def test_every_filter_the_ac_asks_for_is_returned(self):
		params = self._run()["params"]

		# AC: Employee Name & ID, Project, Site, Shift, Role
		self.assertEqual(params["employee_id"], "EMPID-1")
		self.assertEqual(params["employee_name"], "Test Worker")
		self.assertEqual(params["project"], "Project A")
		self.assertEqual(params["site"], "Site A")
		self.assertEqual(params["shift"], "Shift A")
		self.assertEqual(params["operations_role"], "Role A")

	def test_redirects_to_the_roster(self):
		result = self._run()

		self.assertEqual(result["path"], "/app/roster")
		# These two open the right view; the rest are read as page filters.
		self.assertEqual(result["params"]["main_view"], "roster")
		self.assertEqual(result["params"]["sub_view"], "roster")

	def test_calendar_opens_on_the_checker_month(self):
		params = self._run()["params"]

		self.assertEqual(params["year"], "2026")
		self.assertEqual(params["month"], "7")

	def test_allocations_fall_back_to_the_employee_record(self):
		# The checker stores allocations as free text and they can be blank. The Employee
		# record is the fallback, and is the only source for the operations role.
		checker = self._checker(project_allocation="", site_allocation=None, shift_allocation="")
		params = self._run(checker=checker)["params"]

		self.assertEqual(params["project"], "Employee Project")
		self.assertEqual(params["site"], "Employee Site")
		self.assertEqual(params["shift"], "Employee Shift")
		self.assertEqual(params["operations_role"], "Role A")

	def test_employee_identity_falls_back_too(self):
		checker = self._checker(employee_id="", employee_name="")
		params = self._run(checker=checker)["params"]

		self.assertEqual(params["employee_id"], "EMPID-FALLBACK")
		self.assertEqual(params["employee_name"], "Fallback Name")

	def test_missing_employee_record_does_not_raise(self):
		# get_value returns None when the Employee is gone. The button should still open
		# the roster with whatever the checker itself holds rather than erroring.
		params = self._run(employee=None)["params"]

		self.assertEqual(params["project"], "Project A")
		self.assertIsNone(params["operations_role"])

	def test_no_date_falls_back_to_today(self):
		checker = self._checker(date=None)
		params = self._run(checker=checker)["params"]

		today = getdate(frappe.utils.nowdate())
		self.assertEqual(params["year"], str(today.year))
		self.assertEqual(params["month"], str(today.month))
