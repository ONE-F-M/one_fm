# Copyright (c) 2024, ONE FM and Contributors
# See license.txt
"""Tests for the Default Shift Checker's exemptions.

Day Off OT and annual-leave cover are authorised, so they are not evidence of a
mis-allocated shift. Those schedule lines are excluded from the counts behind all
three categories and from the listed dates.
"""

import calendar
from unittest.mock import patch

import frappe
from frappe.query_builder import DocType
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate

from one_fm.operations.doctype.default_shift_checker.default_shift_checker import (
	create_checker,
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

	def test_is_annual_leave_reliever_is_a_real_employee_schedule_field(self):
		self.assertTrue(frappe.get_meta("Employee Schedule").has_field("is_annual_leave_reliever"))

	def test_the_criterion_excludes_day_off_ot_and_annual_leave_cover(self):
		self.assertIn("(EmployeeSchedule.day_off_ot == 0)", self.source)
		self.assertIn("(EmployeeSchedule.is_annual_leave_reliever == 0)", self.source)

	def test_the_count_and_the_date_listing_share_the_criterion(self):
		# create_checker decides *who* is flagged; get_shift_assignments lists the
		# dates. If only one filtered, the count in the comment and the dates shown
		# would disagree.
		self.assertIn("counted_schedule_criterion(EmployeeSchedule) &", self.source)
		self.assertIn("& counted_schedule_criterion(EmployeeSchedule)", self.source)

	def test_the_threshold_must_be_exceeded_not_merely_reached(self):
		# The ACs say "exceeds the Default Shift Checker Threshold", so a count that
		# lands exactly on the limit is compliant.
		self.assertIn("Count(EmployeeSchedule.shift) > threshold", self.source)
		self.assertNotIn("Count(EmployeeSchedule.shift) >= threshold", self.source)


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


# A 31-day month far enough ahead that no real roster rows exist in it.
MONTH_START = getdate("2099-01-01")
MONTH_END = getdate("2099-01-31")


class TestExcusedDaysAreNotCounted(FrappeTestCase):
	"""Runs create_checker against Employee Schedule rows written for one employee."""

	def setUp(self):
		# Rows are written per test; roll them back after each one, not only at class end.
		self.addCleanup(frappe.db.rollback)
		Employee = DocType("Employee")
		Project = DocType("Project")
		rows = (
			frappe.qb.from_(Employee)
			.join(Project).on(Employee.project == Project.name)
			.select(Employee.name, Employee.shift)
			.where(
				(Employee.status == "Active")
				& (Employee.shift_working == 1)
				& Employee.shift.isnotnull()
				& (Employee.shift != "")
				& (Project.custom_exclude_from_default_shift_checker == 0)
			)
			.limit(1)
		).run(as_dict=True)
		if not rows:
			self.skipTest("no active shift-working employee on a checked project")
		self.employee, self.default_shift = rows[0].name, rows[0].shift

		other = frappe.get_all(
			"Operations Shift", filters={"name": ["!=", self.default_shift]}, pluck="name", limit=1
		)
		if not other:
			self.skipTest("needs a second Operations Shift")
		self.other_shift = other[0]

		frappe.db.set_single_value("ONEFM General Setting", "default_shift_checker_threshold", 3)
		self._set_reliever(day_off=0, weekend=0)
		self.next_day = 0

	def _set_reliever(self, day_off, weekend):
		frappe.db.set_value(
			"Employee",
			self.employee,
			{"custom_is_reliever": day_off, "custom_is_weekend_reliever": weekend},
			update_modified=False,
		)

	def _schedule(self, shift, days, day_off_ot=0, annual_leave=0):
		for _ in range(days):
			date = add_days(MONTH_START, self.next_day)
			self.next_day += 1
			frappe.get_doc(
				{
					"doctype": "Employee Schedule",
					"name": f"{date}_{self.employee}_Basic",
					"employee": self.employee,
					"date": date,
					"shift": shift,
					"employee_availability": "Working",
					"roster_type": "Basic",
					"day_off_ot": day_off_ot,
					"is_annual_leave_reliever": annual_leave,
				}
			).db_insert()

	def _run(self, **kwargs):
		# The checker's notification email fails on sites without an outgoing account.
		with patch("frappe.db.commit"), patch("frappe.log_error") as log_error, patch(
			"one_fm.overrides.notification_log.custom_send_notification_email"
		):
			create_checker(MONTH_START, MONTH_END, **kwargs)
		self.assertFalse(log_error.called, msg=log_error.call_args)
		return frappe.get_all(
			"Default Shift Checker",
			filters={"employee": self.employee, "start_date": MONTH_START},
			pluck="name",
		)

	def _listed(self, shift_condition):
		EmployeeSchedule = DocType("Employee Schedule")
		return get_shift_assignments(
			self.employee, shift_condition(EmployeeSchedule), MONTH_START, MONTH_END, EmployeeSchedule
		)

	def test_annual_leave_cover_is_neither_counted_nor_listed(self):
		self._schedule(self.other_shift, 5, annual_leave=1)

		self.assertEqual(self._run(), [])
		self.assertEqual(self._listed(lambda es: es.shift != self.default_shift), {})

	def test_a_mix_is_flagged_only_when_genuine_days_exceed_the_threshold(self):
		self._schedule(self.other_shift, 3)
		self._schedule(self.other_shift, 2, annual_leave=1)
		self._schedule(self.other_shift, 2, day_off_ot=1)
		self.assertEqual(self._run(), [], msg="3 genuine days sit on the threshold of 3")

		self._schedule(self.other_shift, 1)
		flagged = self._run()
		self.assertEqual(len(flagged), 1)

		doc = frappe.get_doc("Default Shift Checker", flagged[0])
		listed = [
			d.strip()
			for row in doc.assigned_shifts_outside_default_shift
			for d in row.schedule_dates.split(",")
		]
		self.assertEqual(sum(row.count for row in doc.assigned_shifts_outside_default_shift), 4)
		self.assertEqual(len(listed), 4)
		self.assertIn("scheduled 4 day(s)", doc.comment)

	def test_weekend_reliever_excused_days_are_not_counted(self):
		self._set_reliever(day_off=0, weekend=1)
		# 27 genuine days is exactly the 31-day-month limit; 4 excused days fill the month.
		self._schedule(self.default_shift, 27)
		self._schedule(self.default_shift, 2, annual_leave=1)
		self._schedule(self.default_shift, 2, day_off_ot=1)

		self.assertEqual(self._run(is_weekend_reliever=True), [])
		listed = self._listed(lambda es: es.shift == self.default_shift)
		self.assertEqual(listed[self.default_shift]["count"], 27)


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
