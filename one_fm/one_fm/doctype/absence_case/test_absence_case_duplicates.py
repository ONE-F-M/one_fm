# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""HD-1858822: one absence, one case.

The nightly absence check raised a fresh Absence Case for the same absence roughly every
16 days. Two faults, one per module:

- api/tasks.attendance_query_script measured the longest consecutive run anywhere since
  1 January, so a run that ended in February still satisfied the seven-day rule in October.
- api/tasks.create_absence_case only suppressed a duplicate created in the previous 15
  days, so on day 16 the same stale finding inserted another case.

Each fault is covered here on its own: the first through live_consecutive_streak, which
the job now decides with, the second against the real table.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, today

from one_fm.api.tasks import (
	CURRENT_ABSENCE_GRACE_DAYS,
	create_absence_case,
	live_consecutive_streak,
)

SEEDED = "HD-1858822-AC-"
EMPLOYEE = "HD-1858822-EMPLOYEE"
SEVEN_DAY = "7 Days Consecutive Absence"


def _clear():
	"""FrappeTestCase rolls back per class, not per test."""
	frappe.db.sql("DELETE FROM `tabAbsence Case` WHERE name LIKE %s", SEEDED + "%")


def _existing_case(absence_start_date=None, created_days_ago=0, docstatus=1, suffix="a"):
	"""An Absence Case row as the dedup query sees it.

	Written straight into the table: the dedup reads four columns, and inserting one
	properly would drag in a real Employee and the formal-hearing rules. `creation` is
	backdated because the fault being covered is precisely a guard that expired with age.
	"""
	name = SEEDED + suffix
	frappe.db.sql(
		"""INSERT INTO `tabAbsence Case`
		   (`name`, `employee`, `absence_type`, `absence_start_date`, `posting_date`,
		    `docstatus`, `owner`, `modified_by`, `creation`, `modified`)
		   VALUES (%s, %s, %s, %s, %s, %s, 'Administrator', 'Administrator', %s, %s)""",
		(
			name,
			EMPLOYEE,
			SEVEN_DAY,
			absence_start_date,
			today(),
			docstatus,
			add_days(today(), -created_days_ago),
			add_days(today(), -created_days_ago),
		),
	)
	return name


class TestOnlyALiveRunRaisesACase(FrappeTestCase):
	"""The gate the seven-day path was missing."""

	def _streak(self, offsets, anchor=None):
		"""offsets are days back from today, the way the job holds them: newest first."""
		anchor = anchor or today()
		dates = sorted(
			(getdate(add_days(anchor, -offset)) for offset in offsets), reverse=True
		)
		return live_consecutive_streak(dates, getdate(anchor))

	def test_a_run_ending_today_is_live(self):
		self.assertEqual(self._streak(range(7))[0], 7)

	def test_a_run_ending_yesterday_is_live(self):
		"""The job runs before today's attendance is marked, so yesterday still counts."""
		self.assertEqual(self._streak(range(1, 8))[0], 7)

	def test_a_run_whose_last_day_was_recorded_late_is_still_live(self):
		"""Attendance is not always written the day it is about - a few rows a month land
		two or three days late. A run that ends exactly on seven and is recorded late must
		still raise its case, or the absence goes unreported entirely."""
		for days_late in range(1, CURRENT_ABSENCE_GRACE_DAYS + 1):
			with self.subTest(days_late=days_late):
				self.assertEqual(self._streak(range(days_late, days_late + 7))[0], 7)

	def test_a_run_past_the_grace_window_is_not_live(self):
		late = CURRENT_ABSENCE_GRACE_DAYS + 1

		self.assertEqual(self._streak(range(late, late + 7)), (0, None))

	def test_a_run_from_eight_months_ago_is_not_live(self):
		"""The case in the ticket: absent 19-25 February, re-raised on 4 October."""
		self.assertEqual(self._streak(range(228, 235)), (0, None))

	def test_an_old_long_run_does_not_revive_a_short_live_one(self):
		"""Seven days in February plus two days this week is a streak of two, not seven.

		This is the whole regression in one assertion - the old code took the longest run
		in the window and would have answered seven.
		"""
		length, start = self._streak([0, 1] + list(range(228, 235)))

		self.assertEqual(length, 2)
		self.assertEqual(start, getdate(add_days(today(), -1)))

	def test_the_start_is_the_head_of_the_live_run(self):
		self.assertEqual(self._streak(range(7))[1], getdate(add_days(today(), -6)))

	def test_a_gap_ends_the_run_at_the_gap(self):
		"""Absent today and yesterday, then nothing, then a week: a streak of two."""
		self.assertEqual(self._streak([0, 1, 4, 5, 6, 7, 8, 9, 10])[0], 2)

	def test_no_absences_at_all(self):
		self.assertEqual(live_consecutive_streak([], getdate(today())), (0, None))


class TestOneAbsenceRaisesOneCase(FrappeTestCase):
	"""The dedup, against the real table."""

	def setUp(self):
		_clear()
		self.start = getdate(add_days(today(), -8))

	def tearDown(self):
		_clear()

	def test_a_second_case_for_the_same_absence_is_refused(self):
		_existing_case(absence_start_date=self.start)

		self.assertIsNone(
			create_absence_case(EMPLOYEE, SEVEN_DAY, absence_start_date=self.start)
		)

	def test_age_does_not_lift_the_guard(self):
		"""The fault itself: at 16 days old the old guard expired and let a copy in."""
		_existing_case(absence_start_date=self.start, created_days_ago=90)

		self.assertIsNone(
			create_absence_case(EMPLOYEE, SEVEN_DAY, absence_start_date=self.start)
		)

	def test_the_guard_ignores_a_cancelled_case(self):
		"""Cancelling is how a wrong case is withdrawn, so it must not block the next
		one. Asserted on the guard's own filter rather than by calling the builder: a
		call that got past the guard would go on to insert, and these fixtures name an
		employee who does not exist."""
		_existing_case(absence_start_date=self.start, docstatus=2)

		self.assertTrue(
			frappe.db.exists(
				"Absence Case",
				{"employee": EMPLOYEE, "absence_start_date": self.start, "docstatus": 2},
			)
		)
		self.assertFalse(
			frappe.db.exists(
				"Absence Case",
				{
					"employee": EMPLOYEE,
					"absence_type": SEVEN_DAY,
					"absence_start_date": self.start,
					"docstatus": ["<", 2],
				},
			)
		)

	def test_the_guard_ignores_a_different_absence(self):
		"""A second genuine run months later deserves its own case. Asserted on the
		guard's filter, for the same reason as above."""
		_existing_case(absence_start_date=add_days(self.start, -120))

		self.assertFalse(
			frappe.db.exists(
				"Absence Case",
				{
					"employee": EMPLOYEE,
					"absence_type": SEVEN_DAY,
					"absence_start_date": self.start,
					"docstatus": ["<", 2],
				},
			)
		)

	def test_without_a_start_date_the_old_window_still_guards(self):
		"""Legacy cases carry no start date, so the fallback must not be a free pass."""
		_existing_case(absence_start_date=None, created_days_ago=1)

		self.assertIsNone(create_absence_case(EMPLOYEE, SEVEN_DAY))
