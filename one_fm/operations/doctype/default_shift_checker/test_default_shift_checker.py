# Copyright (c) 2024, ONE FM and Contributors
# See license.txt
"""Tests for the Default Shift Checker's Day Off OT exemption (WI-001768).

Overtime worked on a day off is authorised, so it is not evidence of a
mis-allocated shift. Schedule lines flagged Day Off OT are excluded from the counts
behind all three categories, or a reliever covering approved Day Off OT trips the
threshold for doing exactly what was asked of them.
"""

import calendar

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from one_fm.operations.doctype.default_shift_checker.default_shift_checker import (
	get_shift_assignments,
	get_weekend_reliever_threshold,
)

SOURCE = (
	"one_fm", "operations", "doctype", "default_shift_checker", "default_shift_checker.py",
)


def _month_bounds(date):
	date = getdate(date)
	return (
		date.replace(day=1),
		date.replace(day=calendar.monthrange(date.year, date.month)[1]),
	)


class TestDefaultShiftChecker(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.source = frappe.read_file(frappe.get_app_path(*SOURCE))

	def test_day_off_ot_is_a_real_employee_schedule_field(self):
		self.assertTrue(frappe.get_meta("Employee Schedule").has_field("day_off_ot"))

	def test_the_selection_query_excludes_day_off_ot(self):
		self.assertIn("(EmployeeSchedule.day_off_ot == 0)", self.source)

	def test_the_date_listing_applies_the_same_exclusion(self):
		# create_checker decides *who* is flagged; get_shift_assignments lists the
		# dates. If only one filtered, the count in the comment and the dates shown
		# would disagree.
		self.assertIn("& (EmployeeSchedule.day_off_ot == 0)", self.source)


class TestGetShiftAssignmentsSkipsDayOffOt(FrappeTestCase):
	"""Exercises the date-listing query against real Employee Schedule rows."""

	def setUp(self):
		row = frappe.db.sql(
			"""
			select es.employee, es.shift, es.date
			from `tabEmployee Schedule` es
			where es.employee_availability = 'Working'
			  and es.roster_type = 'Basic'
			  and es.day_off_ot = 1
			  and ifnull(es.shift, '') != ''
			limit 1
			""",
			as_dict=True,
		)
		if not row:
			self.skipTest("no Day Off OT schedule rows on this instance")
		self.row = row[0]
		self.start, self.end = _month_bounds(self.row.date)

	def _assignments(self):
		EmployeeSchedule = frappe.qb.DocType("Employee Schedule")
		return get_shift_assignments(
			self.row.employee,
			# Matching the shift is how a reliever (Category B/C) is counted.
			EmployeeSchedule.shift == self.row.shift,
			self.start,
			self.end,
			EmployeeSchedule,
		)

	def test_a_day_off_ot_date_is_not_listed(self):
		listed = []
		for data in self._assignments().values():
			listed.extend(d.strip() for d in data["dates"].split(","))
		self.assertNotIn(str(getdate(self.row.date)), listed)

	def test_the_count_matches_the_dates_listed(self):
		for shift, data in self._assignments().items():
			self.assertEqual(
				data["count"],
				len([d for d in data["dates"].split(",") if d.strip()]),
				msg=f"count and dates disagree for {shift}",
			)


class TestWeekendRelieverThreshold(FrappeTestCase):
	"""The process map fixes these two numbers; they are not configuration."""

	def test_a_31_day_month_allows_27(self):
		self.assertEqual(get_weekend_reliever_threshold("2026-03-15"), 27)
		self.assertEqual(get_weekend_reliever_threshold("2026-01-01"), 27)

	def test_a_30_day_month_allows_26(self):
		self.assertEqual(get_weekend_reliever_threshold("2026-04-10"), 26)
		self.assertEqual(get_weekend_reliever_threshold("2026-11-30"), 26)

	def test_a_short_february_allows_26(self):
		self.assertEqual(get_weekend_reliever_threshold("2026-02-10"), 26)


class TestCategoryComments(FrappeTestCase):
	"""The comment is what the supervisor acts on, so its wording is part of the AC."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.source = frappe.read_file(frappe.get_app_path(*SOURCE))

	def test_category_a_is_labelled_a_shift_mismatch(self):
		self.assertIn("Shift Mismatch: Employee is scheduled", self.source)

	def test_category_b_names_the_day_off_reliever_role(self):
		self.assertIn("remove the employee from the Day OFF Reliever role", self.source)

	def test_category_c_names_the_weekend_reliever_role(self):
		self.assertIn("remove the employee from the Weekend Reliever role", self.source)
