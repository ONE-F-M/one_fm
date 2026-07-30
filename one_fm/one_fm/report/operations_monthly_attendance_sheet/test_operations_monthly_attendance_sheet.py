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
	MAX_RANGE_DAYS,
	execute,
	get_columns,
	get_columns_for_days,
	get_date_range,
	get_report_additional_day_details,
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
