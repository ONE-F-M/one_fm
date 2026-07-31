# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for the date-range Operations Monthly Attendance Sheet (WI-001790).

The report used to take Month + Year and key every cell by day-of-month. It now
takes a From/To range, which means two days in different months can share a day
number - so cells are keyed by ISO date instead.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate

from one_fm.one_fm.report.operations_monthly_attendance_sheet.operations_monthly_attendance_sheet import (
	BY_SHIFT_HOURS,
	MAX_RANGE_DAYS,
	apply_roster_type_filters,
	execute,
	format_shift_hours,
	get_attendance_status,
	get_columns,
	get_columns_for_days,
	get_date_range,
	get_message,
	get_report_additional_day_details,
	is_invalid_roster_combination,
	merge_hours_maps,
	validate_filters,
)

FROM_DATE = "2026-01-10"
TO_DATE = "2026-01-16"


def _filters(**kwargs):
	base = {"from_date": FROM_DATE, "to_date": TO_DATE, "generate": 1}
	base.update(kwargs)
	return frappe._dict(base)


class TestDateRange(FrappeTestCase):
	def test_the_range_is_inclusive_of_both_ends(self):
		dates = get_date_range(_filters())
		self.assertEqual(len(dates), 7)
		self.assertEqual(dates[0], getdate(FROM_DATE))
		self.assertEqual(dates[-1], getdate(TO_DATE))

	def test_a_single_day_is_a_valid_range(self):
		self.assertEqual(len(get_date_range(_filters(to_date=FROM_DATE))), 1)

	def test_a_range_crossing_a_month_boundary(self):
		# The case day-of-month keying could not represent.
		dates = get_date_range(_filters(from_date="2025-12-28", to_date="2026-01-05"))
		self.assertEqual(len(dates), 9)
		self.assertEqual(len({str(d) for d in dates}), 9)


class TestValidateFilters(FrappeTestCase):
	def test_missing_dates_are_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			validate_filters(frappe._dict(from_date=None, to_date=None))

	def test_a_reversed_range_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			validate_filters(frappe._dict(from_date=TO_DATE, to_date=FROM_DATE))

	def test_an_over_long_range_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			validate_filters(
				frappe._dict(from_date=FROM_DATE, to_date=add_days(FROM_DATE, MAX_RANGE_DAYS))
			)

	def test_the_maximum_range_is_allowed(self):
		validate_filters(
			frappe._dict(from_date=FROM_DATE, to_date=add_days(FROM_DATE, MAX_RANGE_DAYS - 1))
		)


class TestColumns(FrappeTestCase):
	def test_day_columns_are_keyed_by_iso_date(self):
		columns = get_columns_for_days(get_date_range(_filters()))
		self.assertEqual(len(columns), 7)
		self.assertEqual(columns[0]["fieldname"], FROM_DATE)
		self.assertEqual(columns[-1]["fieldname"], TO_DATE)

	def test_day_labels_carry_the_month(self):
		# A range spanning two months would otherwise show two ambiguous "3"s.
		labels = [c["label"] for c in get_columns_for_days(get_date_range(_filters()))]
		self.assertEqual(labels[0], "10 Jan Sat")

	def test_the_attribute_columns_the_ac_lists_are_present(self):
		fieldnames = [c["fieldname"] for c in get_columns(_filters(), [])]
		for expected in (
			"employee_id", "employee_name", "project", "employee_status",
			"employment_type", "roster_type", "day_off_ot", "shift",
		):
			self.assertIn(expected, fieldnames)

	def test_column_keys_are_unique(self):
		fieldnames = [c["fieldname"] for c in get_columns(_filters(), get_date_range(_filters()))]
		self.assertEqual(len(fieldnames), len(set(fieldnames)))


class TestGenerateGate(FrappeTestCase):
	"""The report must open empty; a payroll extract is too costly to auto-run."""

	def test_nothing_is_queried_until_generate_is_set(self):
		columns, data, message = execute(_filters(generate=0))
		self.assertEqual(data, [])
		self.assertIn("Generate", message)

	def test_no_day_columns_are_offered_before_generating(self):
		columns, data, _msg = execute(_filters(generate=0))
		self.assertEqual([c for c in columns if c.get("width") == 65], [])

	def test_dates_are_not_validated_before_generating(self):
		# Opening the report with no dates yet must not throw in the user's face.
		execute(frappe._dict(generate=0))


class TestDayHeaders(FrappeTestCase):
	def test_headers_cover_the_range_and_carry_the_row_key(self):
		days = get_report_additional_day_details(FROM_DATE, TO_DATE)
		self.assertEqual(len(days), 7)
		self.assertEqual(days[0]["key"], FROM_DATE)
		self.assertEqual(days[0]["date"], 10)
		self.assertEqual(days[0]["month"], "Jan")
		self.assertEqual(days[0]["weekday"], "Sat")

	def test_headers_reject_an_invalid_range(self):
		with self.assertRaises(frappe.ValidationError):
			get_report_additional_day_details(TO_DATE, FROM_DATE)


class TestAgainstRealData(FrappeTestCase):
	"""Every populated cell must land on a declared column."""

	def setUp(self):
		row = frappe.db.sql(
			"""
			select year(attendance_date) as y, month(attendance_date) as mo
			from `tabAttendance` where docstatus = 1
			group by y, mo order by count(*) desc limit 1
			""",
			as_dict=True,
		)
		if not row:
			self.skipTest("no submitted attendance on this instance")
		from frappe.utils import get_first_day, get_last_day

		anchor = getdate(f"{row[0].y}-{row[0].mo:02d}-01")
		self.lo, self.hi = get_first_day(anchor), get_last_day(anchor)

	def test_rows_only_use_declared_columns(self):
		columns, data = execute(_filters(from_date=self.lo, to_date=self.hi))[:2]
		if not data:
			self.skipTest("no rows for the busiest month")
		declared = {c["fieldname"] for c in columns}
		for row in data[:50]:
			self.assertEqual([k for k in row if k not in declared], [], msg=str(row)[:120])

	def test_a_part_month_range_returns_rows(self):
		columns, data = execute(
			_filters(from_date=self.lo, to_date=add_days(self.lo, 6))
		)[:2]
		self.assertEqual(len([c for c in columns if c.get("width") == 65]), 7)
		if data:
			day_fields = [c["fieldname"] for c in columns if c.get("width") == 65]
			self.assertTrue(any(row.get(f) for row in data for f in day_fields))



def _roster_sql(**filters):
	"""The SQL apply_roster_type_filters produces, for asserting on the conditions."""
	Attendance = frappe.qb.DocType("Attendance")
	query = frappe.qb.from_(Attendance).select(Attendance.employee)

	return apply_roster_type_filters(
		query, Attendance.roster_type, Attendance.day_off_ot, frappe._dict(filters)
	).get_sql()


class TestRosterTypeRules(FrappeTestCase):
	"""WI-001791 Logic Rules 1-4, on the query both source tables share."""

	def test_rule_1_basic_alone_excludes_day_off_ot(self):
		# "must actively hide any Overtime data or Basic Day Off OT data" - the roster
		# type takes care of Overtime, the negative takes care of the day-off OT rows.
		sql = _roster_sql(roster_type="Basic", day_off_ot=0)
		self.assertIn('`roster_type`=\'Basic\'', sql)
		self.assertIn('`day_off_ot`<>1', sql)

	def test_rule_2_basic_with_day_off_ot_keeps_only_those_rows(self):
		sql = _roster_sql(roster_type="Basic", day_off_ot=1)
		self.assertIn('`roster_type`=\'Basic\'', sql)
		self.assertIn('`day_off_ot`=1', sql)
		self.assertNotIn("<>1", sql)

	def test_rule_3_overtime_alone_constrains_only_the_roster_type(self):
		# Its edge case asks for the basic rows to be hidden, which the roster type
		# already does; overtime worked on a day off stays visible here.
		sql = _roster_sql(roster_type="Over-Time", day_off_ot=0)
		self.assertIn("Over-Time", sql)
		self.assertNotIn("day_off_ot", sql)

	def test_rule_4_is_refused_before_any_query(self):
		self.assertTrue(is_invalid_roster_combination(frappe._dict(roster_type="Over-Time", day_off_ot=1)))
		self.assertFalse(is_invalid_roster_combination(frappe._dict(roster_type="Basic", day_off_ot=1)))
		self.assertFalse(is_invalid_roster_combination(frappe._dict(roster_type="Over-Time", day_off_ot=0)))

	def test_rule_4_returns_an_empty_report_with_an_explanation(self):
		columns, data, message = execute(_filters(roster_type="Over-Time", day_off_ot=1))
		self.assertEqual(data, [])
		self.assertIn("not a valid combination", message)
		# The columns are still built so the table renders its empty state.
		self.assertTrue(columns)

	def test_no_roster_type_is_left_unconstrained(self):
		self.assertNotIn("roster_type", _roster_sql(roster_type="", day_off_ot=0))

	def test_day_off_ot_alone_still_narrows_to_those_rows(self):
		sql = _roster_sql(roster_type="", day_off_ot=1)
		self.assertIn('`day_off_ot`=1', sql)
		self.assertNotIn("roster_type", sql)


class TestShiftHours(FrappeTestCase):
	"""WI-001791: the cells show the scheduled duration, never the clocked hours."""

	DATES = [getdate("2026-01-10"), getdate("2026-01-11"), getdate("2026-01-12")]

	def _rows(self, generate_based_on):
		return get_attendance_status(
			self.DATES,
			{"Morning": {self.DATES[0]: "Present", self.DATES[1]: "Absent"}},
			{self.DATES[2]: "Day Off"},
			None,
			{},
			{"Morning": {self.DATES[0]: 12.0, self.DATES[1]: 12.0}},
			generate_based_on,
		)

	def test_the_cells_carry_the_scheduled_duration(self):
		row = self._rows(BY_SHIFT_HOURS)[0]
		self.assertEqual(row[str(self.DATES[0])], "12")
		# Scheduled is scheduled: an absent day still had a 12 hour shift rostered.
		self.assertEqual(row[str(self.DATES[1])], "12")

	def test_a_day_with_no_shift_stays_empty(self):
		# The day off has no scheduled shift, so there are no hours to show.
		self.assertEqual(self._rows(BY_SHIFT_HOURS)[0][str(self.DATES[2])], "")

	def test_attendance_status_mode_is_unchanged(self):
		row = self._rows("Attendance Status")[0]
		self.assertEqual(row[str(self.DATES[0])], "P")
		self.assertEqual(row[str(self.DATES[1])], "A")
		self.assertEqual(row[str(self.DATES[2])], "DO")

	def test_the_totals_agree_across_both_modes(self):
		# Counts come off the status either way, so switching mode cannot move them.
		for mode in (BY_SHIFT_HOURS, "Attendance Status"):
			row = self._rows(mode)[0]
			self.assertEqual((row["working_days"], row["off_days"]), (1, 1), msg=mode)

	def test_the_legend_describes_what_the_cells_hold(self):
		hours_message = get_message(frappe._dict(generate_based_on=BY_SHIFT_HOURS))
		self.assertIn("scheduled duration", hours_message)
		# The status legend has no meaning in that mode and must not appear.
		self.assertNotIn("Present - P", hours_message)
		self.assertIn("Present - P", get_message(frappe._dict(generate_based_on="Attendance Status")))


class TestFormatShiftHours(FrappeTestCase):
	def test_whole_hours_lose_the_decimal(self):
		# The AC writes them as 8, 10, 12 - not 8.0.
		self.assertEqual(format_shift_hours(8.0), "8")
		self.assertEqual(format_shift_hours(12), "12")

	def test_part_hours_are_kept(self):
		self.assertEqual(format_shift_hours(7.5), "7.5")

	def test_nothing_scheduled_shows_nothing(self):
		self.assertEqual(format_shift_hours(0), "")
		self.assertEqual(format_shift_hours(None), "")


class TestMergeHoursMaps(FrappeTestCase):
	def test_later_maps_win_per_day(self):
		merged = merge_hours_maps(
			{"EMP-1": {"Morning": {"2026-01-10": 8.0, "2026-01-11": 8.0}}},
			{"EMP-1": {"Morning": {"2026-01-11": 12.0}}},
		)
		self.assertEqual(merged["EMP-1"]["Morning"], {"2026-01-10": 8.0, "2026-01-11": 12.0})

	def test_shifts_and_employees_are_kept_side_by_side(self):
		merged = merge_hours_maps(
			{"EMP-1": {"Morning": {"2026-01-10": 8.0}}},
			{"EMP-1": {"Evening": {"2026-01-10": 12.0}}, "EMP-2": {"Night": {"2026-01-10": 9.0}}},
		)
		self.assertEqual(set(merged["EMP-1"]), {"Morning", "Evening"})
		self.assertEqual(merged["EMP-2"]["Night"]["2026-01-10"], 9.0)

	def test_an_empty_map_is_tolerated(self):
		self.assertEqual(merge_hours_maps({}, None), {})
