# Copyright (c) 2026, ONE FM and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, date_diff, getdate

from one_fm.operations.doctype.roster_double_shift_ot_checker.roster_double_shift_ot_checker import (
	build_double_shift_ot_dates,
	build_double_shift_ot_explanation,
	format_monthweek,
	get_check_periods,
)


class TestRosterDoubleShiftOTChecker(FrappeTestCase):
	def test_two_consecutive_full_weeks(self):
		(week1_start, week1_end), (week2_start, week2_end) = get_check_periods("2026-07-25")

		self.assertEqual(date_diff(week1_end, week1_start), 6)
		self.assertEqual(date_diff(week2_end, week2_start), 6)
		self.assertEqual(week2_start, add_days(week1_end, 1))

	def test_current_week_contains_the_given_date(self):
		date = getdate("2026-07-25")
		(week1_start, week1_end), _ = get_check_periods(date)

		self.assertLessEqual(week1_start, date)
		self.assertLessEqual(date, week1_end)

	def test_periods_are_stable_across_the_week(self):
		# repeat_count relies on the label being identical on consecutive runs within a week
		date = getdate("2026-07-25")
		week_start = get_check_periods(date)[0][0]

		self.assertEqual(get_check_periods(week_start), get_check_periods(date))

	def test_monthweek_label_format(self):
		self.assertEqual(format_monthweek("2026-07-20", "2026-07-26"), "Jul 20 - Jul 26")

	def test_dates_list_one_line_per_schedule(self):
		schedules = [
			frappe._dict(date="2026-07-20", shift="SHIFT-A"),
			frappe._dict(date="2026-07-22", shift="SHIFT-B"),
		]
		self.assertEqual(
			build_double_shift_ot_dates(schedules), "2026-07-20 (SHIFT-A)\n2026-07-22 (SHIFT-B)"
		)

	def test_explanation_counts_schedules_and_distinct_shifts(self):
		schedules = [
			frappe._dict(date="2026-07-20", shift="SHIFT-A"),
			frappe._dict(date="2026-07-21", shift="SHIFT-A"),
			frappe._dict(date="2026-07-22", shift="SHIFT-B"),
		]
		explanation = build_double_shift_ot_explanation(schedules)

		self.assertIn("3 Over-Time schedule(s)", explanation)
		self.assertIn("2 shift(s)", explanation)

	def test_explanation_fits_the_data_field(self):
		# double_shift_ot_explanation is a Data field (varchar 140)
		schedules = [frappe._dict(date="2026-07-20", shift="SHIFT-A")]
		self.assertLessEqual(len(build_double_shift_ot_explanation(schedules)), 140)
