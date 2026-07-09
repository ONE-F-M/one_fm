# Copyright (c) 2022, ONE FM and Contributors
# See license.txt

from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from one_fm.operations.doctype.roster_day_off_checker.roster_day_off_checker import (
	is_exit_before_month_midpoint,
)


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
