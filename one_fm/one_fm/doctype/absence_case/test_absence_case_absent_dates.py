# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002465: the absent dates an Absence Case is about, and the jump to Attendance.

The dates are read off Attendance rather than typed, so the fixtures here are Attendance
rows written straight into the table: Attendance has its own validations - a shift, a
duplicate check, a leave application - and none of them has anything to do with which days
somebody was marked absent.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, today

from one_fm.one_fm.doctype.absence_case.absence_case import (
	ABSENT,
	CONSECUTIVE_LOOKBACK_DAYS,
	absent_attendance_dates,
	consecutive_run,
	is_consecutive,
	threshold_days,
)

SEEDED = "WI-002465-ATT-"
EMPLOYEE = "WI-002465-EMPLOYEE"


def _clear():
	"""FrappeTestCase rolls back per class, not per test."""
	frappe.db.sql("DELETE FROM `tabAttendance` WHERE name LIKE %s", SEEDED + "%")


def _attendance(date, status=ABSENT, docstatus=1, employee=EMPLOYEE, suffix=None):
	"""One Attendance row, written without running Attendance's own validations."""
	name = SEEDED + (suffix or f"{employee}-{date}")
	frappe.db.sql(
		"""INSERT INTO `tabAttendance`
		   (`name`, `employee`, `attendance_date`, `status`, `docstatus`,
		    `owner`, `modified_by`, `creation`, `modified`)
		   VALUES (%s, %s, %s, %s, %s, 'Administrator', 'Administrator', NOW(), NOW())""",
		(name, employee, date, status, docstatus),
	)
	return name


def _case(absence_type, absence_start_date=None, posting_date=None, employee=EMPLOYEE):
	"""An Absence Case as validate sees it. Built in memory - the rule reads four fields,
	and inserting one would drag in the formal-hearing rules and a real Employee."""
	doc = frappe.new_doc("Absence Case")
	doc.employee = employee
	doc.absence_type = absence_type
	doc.absence_start_date = absence_start_date
	doc.posting_date = posting_date or today()
	return doc


def _dates(doc):
	doc.set_absent_dates()
	return [line for line in (doc.absent_dates or "").split("\n") if line]


class TestReadingTheAbsenceType(FrappeTestCase):
	"""Both halves of the behaviour are read out of the option's own words, so every
	option the field offers has to parse - this site has four, not the two the story
	names."""

	def test_every_option_the_field_offers_names_a_number(self):
		options = [
			option
			for option in frappe.get_meta("Absence Case").get_field("absence_type").options.split("\n")
			if option
		]

		self.assertTrue(options)
		for option in options:
			with self.subTest(option=option):
				self.assertIsNotNone(threshold_days(option), f"{option!r} names no number")

	def test_the_two_the_story_names_are_offered(self):
		options = frappe.get_meta("Absence Case").get_field("absence_type").options

		self.assertIn("7 Days Consecutive Absence", options)
		self.assertIn("21 Days Absence in a Year", options)

	def test_the_site_s_other_two_are_still_offered(self):
		"""5 and 16 day cases are raised by attendance_query_script and must not be lost."""
		options = frappe.get_meta("Absence Case").get_field("absence_type").options

		self.assertIn("5 Days Consecutive Absence", options)
		self.assertIn("16 Days Absence in a Year", options)

	def test_consecutive_is_told_from_yearly(self):
		self.assertTrue(is_consecutive("7 Days Consecutive Absence"))
		self.assertTrue(is_consecutive("5 Days Consecutive Absence"))
		self.assertFalse(is_consecutive("21 Days Absence in a Year"))
		self.assertFalse(is_consecutive("16 Days Absence in a Year"))

	def test_the_number_is_the_one_in_the_name(self):
		self.assertEqual(threshold_days("7 Days Consecutive Absence"), 7)
		self.assertEqual(threshold_days("21 Days Absence in a Year"), 21)
		self.assertIsNone(threshold_days(None))
		self.assertIsNone(threshold_days("Absence"))


class TestFindingOneRun(FrappeTestCase):
	"""consecutive_run on its own - no database, so the date arithmetic is checked
	without a fixture."""

	def _days(self, *offsets):
		return [getdate(add_days("2026-06-10", offset)) for offset in offsets]

	def test_an_empty_list_has_no_run(self):
		self.assertEqual(consecutive_run([]), [])

	def test_the_latest_run_is_taken_when_no_start_is_given(self):
		dates = self._days(0, 1, 2, 9, 10)

		self.assertEqual(consecutive_run(dates), self._days(9, 10))

	def test_a_start_picks_the_run_it_falls_in(self):
		dates = self._days(0, 1, 2, 9, 10)

		self.assertEqual(consecutive_run(dates, "2026-06-10"), self._days(0, 1, 2))

	def test_a_start_inside_a_run_takes_the_rest_of_it(self):
		dates = self._days(0, 1, 2, 3)

		self.assertEqual(consecutive_run(dates, "2026-06-12"), self._days(2, 3))

	def test_a_start_in_no_run_finds_nothing(self):
		dates = self._days(0, 1, 2)

		self.assertEqual(consecutive_run(dates, "2026-06-20"), [])

	def test_one_day_is_a_run(self):
		self.assertEqual(consecutive_run(self._days(0)), self._days(0))


class TestWhichAttendanceCounts(FrappeTestCase):
	def setUp(self):
		_clear()

	def tearDown(self):
		_clear()

	def test_only_submitted_absences_count(self):
		_attendance(add_days(today(), -3), suffix="a")
		_attendance(add_days(today(), -2), status="Present", suffix="b")
		_attendance(add_days(today(), -1), docstatus=0, suffix="c")
		_attendance(today(), docstatus=2, suffix="d")

		found = absent_attendance_dates(EMPLOYEE, add_days(today(), -10), today())

		self.assertEqual(found, [getdate(add_days(today(), -3))])

	def test_another_employee_is_not_counted(self):
		_attendance(add_days(today(), -1), employee="WI-002465-OTHER", suffix="other")

		self.assertEqual(absent_attendance_dates(EMPLOYEE, add_days(today(), -10), today()), [])


class TestAConsecutiveCase(FrappeTestCase):
	"""AC 3, first half."""

	def setUp(self):
		_clear()
		self.start = add_days(today(), -9)
		for offset in range(9):
			_attendance(add_days(self.start, offset), suffix=f"run{offset}")

	def tearDown(self):
		_clear()

	def test_it_lists_the_days_the_type_names(self):
		"""Nine absent days in a row, on a seven day case - seven of them."""
		dates = _dates(_case("7 Days Consecutive Absence", absence_start_date=self.start))

		self.assertEqual(dates, [str(getdate(add_days(self.start, n))) for n in range(7)])

	def test_a_five_day_case_lists_five(self):
		dates = _dates(_case("5 Days Consecutive Absence", absence_start_date=self.start))

		self.assertEqual(len(dates), 5)
		self.assertEqual(dates[0], str(getdate(self.start)))

	def test_it_starts_where_the_case_says(self):
		dates = _dates(
			_case("7 Days Consecutive Absence", absence_start_date=add_days(self.start, 2))
		)

		self.assertEqual(dates[0], str(getdate(add_days(self.start, 2))))

	def test_it_finds_the_run_without_a_start_date(self):
		"""The nightly job only passes a start date for a 5 day case; the 7 day path never
		has, so without this the field would stay empty for the type AC 3 names."""
		dates = _dates(_case("7 Days Consecutive Absence"))

		self.assertEqual(dates, [str(getdate(add_days(self.start, n))) for n in range(7)])

	def test_a_gap_ends_the_run(self):
		_clear()
		for offset in (0, 1, 2, 4, 5):
			_attendance(add_days(self.start, offset), suffix=f"gap{offset}")

		dates = _dates(_case("7 Days Consecutive Absence", absence_start_date=self.start))

		self.assertEqual(dates, [str(getdate(add_days(self.start, n))) for n in range(3)])

	def test_nothing_to_find_is_an_empty_field(self):
		_clear()

		self.assertEqual(_dates(_case("7 Days Consecutive Absence")), [])

	def test_an_absence_older_than_the_lookback_is_not_dragged_in(self):
		_clear()
		old = add_days(today(), -(CONSECUTIVE_LOOKBACK_DAYS + 5))
		_attendance(old, suffix="old")

		self.assertEqual(_dates(_case("7 Days Consecutive Absence")), [])


class TestAYearlyCase(FrappeTestCase):
	"""AC 3, second half."""

	def setUp(self):
		_clear()
		self.year = getdate(today()).year

	def tearDown(self):
		_clear()

	def test_it_lists_the_year_s_absences(self):
		days = [f"{self.year}-01-05", f"{self.year}-03-17", f"{self.year}-07-02"]
		for day in days:
			_attendance(day, suffix=day)

		self.assertEqual(_dates(_case("21 Days Absence in a Year")), days)

	def test_another_year_is_left_out(self):
		_attendance(f"{self.year - 1}-12-31", suffix="prev")
		_attendance(f"{self.year}-01-01", suffix="this")

		self.assertEqual(_dates(_case("21 Days Absence in a Year")), [f"{self.year}-01-01"])

	def test_it_is_not_capped_at_the_threshold(self):
		"""The number in the type is what raised the case; an employee absent more days
		than that is not verified by being shown fewer of them."""
		days = [f"{self.year}-02-{day:02d}" for day in range(1, 26)]
		for day in days:
			_attendance(day, suffix=day)

		self.assertEqual(len(_dates(_case("21 Days Absence in a Year"))), 25)

	def test_the_year_is_the_case_s_own(self):
		"""Read off posting_date, so a case raised last year still describes last year."""
		_attendance(f"{self.year - 1}-05-04", suffix="prev")

		dates = _dates(
			_case("21 Days Absence in a Year", posting_date=f"{self.year - 1}-12-01")
		)

		self.assertEqual(dates, [f"{self.year - 1}-05-04"])


class TestWhenNothingIsAsked(FrappeTestCase):
	def setUp(self):
		_clear()
		_attendance(add_days(today(), -1), suffix="one")

	def tearDown(self):
		_clear()

	def test_no_absence_type_means_no_dates(self):
		"""The fields are hidden in that state, and a stale list behind a hidden field is
		worse than an empty one."""
		self.assertEqual(_dates(_case(None)), [])

	def test_no_employee_means_no_dates(self):
		self.assertEqual(_dates(_case("7 Days Consecutive Absence", employee=None)), [])


class TestTheFieldsTheStoryAdds(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.meta = frappe.get_meta("Absence Case")

	def test_absent_dates_matches_the_ba_site(self):
		field = self.meta.get_field("absent_dates")

		self.assertIsNotNone(field)
		self.assertEqual(field.fieldtype, "Long Text")
		self.assertEqual(field.label, "Absent Dates")
		self.assertTrue(field.read_only)

	def test_go_to_attendance_matches_the_ba_site(self):
		field = self.meta.get_field("go_to_attendance")

		self.assertIsNotNone(field)
		self.assertEqual(field.fieldtype, "Button")
		self.assertEqual(field.label, "Go to Attendance")
		# The case is submittable and the jump has to work on a submitted one.
		self.assertTrue(field.allow_on_submit)

	def test_both_hide_until_an_absence_type_is_chosen(self):
		"""AC 1, and the same expression the BA site uses."""
		for fieldname in ("absent_dates", "go_to_attendance"):
			with self.subTest(fieldname=fieldname):
				self.assertEqual(self.meta.get_field(fieldname).depends_on, "eval:doc.absence_type")

	def test_they_sit_under_the_absence_type(self):
		order = [field.fieldname for field in self.meta.fields]

		self.assertEqual(
			order[order.index("absence_type") : order.index("absence_type") + 3],
			["absence_type", "absent_dates", "go_to_attendance"],
		)


class TestTheJobSetsAStartDate(FrappeTestCase):
	"""WI-002465: every type carries the day its absence began, not only the 5-day one.

	Without it the Absent Dates field on a 7-day case had nothing to start from, which is
	the type AC 3 actually names.
	"""

	def _run_start(self, offsets, minimum, anchor="2026-06-10"):
		from one_fm.api.tasks import latest_consecutive_run_start

		return latest_consecutive_run_start(
			[getdate(add_days(anchor, offset)) for offset in offsets], minimum
		)

	def test_it_finds_the_head_of_a_qualifying_run(self):
		self.assertEqual(self._run_start(range(7), 7), getdate("2026-06-10"))

	def test_a_run_one_day_short_does_not_qualify(self):
		self.assertIsNone(self._run_start(range(6), 7))

	def test_the_most_recent_qualifying_run_wins(self):
		"""Two runs of seven; the live one is what the case was raised about."""
		offsets = list(range(7)) + list(range(20, 27))

		self.assertEqual(self._run_start(offsets, 7), getdate(add_days("2026-06-10", 20)))

	def test_a_longer_earlier_run_does_not_win_over_a_recent_one(self):
		offsets = list(range(10)) + list(range(30, 37))

		self.assertEqual(self._run_start(offsets, 7), getdate(add_days("2026-06-10", 30)))

	def test_a_gap_breaks_the_run(self):
		offsets = [0, 1, 2, 4, 5, 6, 7]

		self.assertIsNone(self._run_start(offsets, 7))

	def test_it_is_the_head_of_the_run_not_the_seventh_day(self):
		"""Ten days in a row on a seven day case starts at day one, so the case lists the
		first seven rather than the last."""
		self.assertEqual(self._run_start(range(10), 7), getdate("2026-06-10"))

	def test_no_absences_at_all(self):
		self.assertIsNone(self._run_start([], 7))

	def test_unsorted_input_is_handled(self):
		"""The caller holds its dates newest-first."""
		self.assertEqual(self._run_start(list(reversed(range(7))), 7), getdate("2026-06-10"))


class TestTheStartDateReachesTheCase(FrappeTestCase):
	"""End to end: what the job now puts on the case is what makes the field populate."""

	def setUp(self):
		_clear()
		self.start = add_days(today(), -8)
		for offset in range(8):
			_attendance(add_days(self.start, offset), suffix=f"e2e{offset}")

	def tearDown(self):
		_clear()

	def test_the_job_would_pick_the_run_the_controller_then_lists(self):
		from one_fm.api.tasks import latest_consecutive_run_start

		absent = absent_attendance_dates(EMPLOYEE, add_days(today(), -30), today())
		start = latest_consecutive_run_start(absent, 7)

		self.assertEqual(start, getdate(self.start))

		dates = _dates(_case("7 Days Consecutive Absence", absence_start_date=start))
		self.assertEqual(dates, [str(getdate(add_days(self.start, n))) for n in range(7)])

	def test_the_milestone_builder_accepts_a_start_date(self):
		"""create_yearly_milestone_absence_case gained the argument; a signature change
		that silently dropped it would leave yearly cases blank again."""
		import inspect

		from one_fm.api.tasks import create_absence_case, create_yearly_milestone_absence_case

		for builder in (create_absence_case, create_yearly_milestone_absence_case):
			with self.subTest(builder=builder.__name__):
				self.assertIn(
					"absence_start_date", inspect.signature(builder).parameters
				)
