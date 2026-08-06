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
	SUMMARY_COUNTERS,
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
	row_group,
	summary_counter,
	validate_filters,
)

REPORT = "Operations Monthly Attendance Sheet"

FROM_DATE = "2026-01-10"
TO_DATE = "2026-01-16"


def _filters(**kwargs):
	base = {"from_date": FROM_DATE, "to_date": TO_DATE}
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
			"employment_type", "roster_type", "day_off_ot",
		):
			self.assertIn(expected, fieldnames)

	def test_no_column_the_ac_does_not_list_is_shown(self):
		# WI-001790 enumerates the columns to display; Shift is not among them. The
		# hidden employee column is excluded - it carries the docname for the in-page
		# filters and renders nothing.
		allowed = {
			"employee", "employee_id", "employee_name", "project", "employee_status",
			"employment_type", "roster_type", "day_off_ot",
			"working_days", "off_days", "total_hours",
			# WI-001979 added the rest of the summary block.
			*SUMMARY_COUNTERS,
		}
		shown = {
			c["fieldname"]
			for c in get_columns(_filters(), [])
			if not c.get("hidden")
		}
		self.assertEqual(shown - allowed, set())
		self.assertNotIn("shift", shown)

	def test_column_keys_are_unique(self):
		fieldnames = [c["fieldname"] for c in get_columns(_filters(), get_date_range(_filters()))]
		self.assertEqual(len(fieldnames), len(set(fieldnames)))


class TestTheRunIsDeferred(FrappeTestCase):
	"""A payroll extract over every employee is too costly to run on each filter
	change. That is the prepared report's job - it queues the run in the background and
	offers "Generate New Report" - so the report no longer carries a Generate gate of
	its own, which duplicated the framework's button.
	"""

	def test_the_report_is_a_prepared_report(self):
		self.assertTrue(frappe.db.get_value("Report", REPORT, "prepared_report"))

	def test_no_generate_filter_is_declared(self):
		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "one_fm", "report", "operations_monthly_attendance_sheet",
				"operations_monthly_attendance_sheet.js",
			)
		)
		self.assertNotIn('fieldname: "generate"', source)
		self.assertNotIn('add_inner_button(__("Generate")', source)


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
	# The maps are keyed by the row group from WI-001790: shift, roster type and the
	# Day Off OT flag.
	GROUP = ("Morning", "Basic", 0, "")

	def _rows(self, generate_based_on):
		return get_attendance_status(
			self.DATES,
			{self.GROUP: {self.DATES[0]: "Present", self.DATES[1]: "Absent"}},
			{self.DATES[2]: "Day Off"},
			None,
			{},
			{self.GROUP: {self.DATES[0]: 12.0, self.DATES[1]: 12.0}},
			generate_based_on,
		)

	def test_the_row_names_its_group(self):
		# Shift is part of the group key but is not a column, so the row carries only the
		# two attributes WI-001790 lists.
		row = self._rows(BY_SHIFT_HOURS)[0]
		_shift, roster_type, day_off_ot, _project = self.GROUP
		self.assertEqual((row["roster_type"], row["day_off_ot"]), (roster_type, day_off_ot))
		self.assertNotIn("shift", row)

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
	MORNING = ("Morning", "Basic", 0, "")
	EVENING = ("Evening", "Basic", 0, "")
	NIGHT = ("Night", "Basic", 0, "")
	MORNING_OT = ("Morning", "Over-Time", 0, "")

	def test_later_maps_win_per_day(self):
		merged = merge_hours_maps(
			{"EMP-1": {self.MORNING: {"2026-01-10": 8.0, "2026-01-11": 8.0}}},
			{"EMP-1": {self.MORNING: {"2026-01-11": 12.0}}},
		)
		self.assertEqual(merged["EMP-1"][self.MORNING], {"2026-01-10": 8.0, "2026-01-11": 12.0})

	def test_groups_and_employees_are_kept_side_by_side(self):
		merged = merge_hours_maps(
			{"EMP-1": {self.MORNING: {"2026-01-10": 8.0}}},
			{"EMP-1": {self.EVENING: {"2026-01-10": 12.0}}, "EMP-2": {self.NIGHT: {"2026-01-10": 9.0}}},
		)
		self.assertEqual(set(merged["EMP-1"]), {self.MORNING, self.EVENING})
		self.assertEqual(merged["EMP-2"][self.NIGHT]["2026-01-10"], 9.0)

	def test_one_shift_on_two_roster_types_keeps_its_hours_apart(self):
		# The reason the map is keyed by the group and not by the shift.
		merged = merge_hours_maps(
			{"EMP-1": {self.MORNING: {"2026-01-10": 8.0}}},
			{"EMP-1": {self.MORNING_OT: {"2026-01-10": 4.0}}},
		)
		self.assertEqual(merged["EMP-1"][self.MORNING]["2026-01-10"], 8.0)
		self.assertEqual(merged["EMP-1"][self.MORNING_OT]["2026-01-10"], 4.0)

	def test_an_empty_map_is_tolerated(self):
		self.assertEqual(merge_hours_maps({}, None), {})

class TestRosterTypeAndDayOffOTAreCarried(FrappeTestCase):
	"""Both were declared as columns and used as filters, but nothing ever put them on
	a row, so they rendered blank down the whole report. A row is now one shift AND one
	roster type AND one Day Off OT flag, which is what lets them carry a value.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.data = execute(_filters())[1]

	def test_the_columns_are_declared(self):
		names = {c["fieldname"] for c in execute(_filters())[0]}
		self.assertIn("roster_type", names)
		self.assertIn("day_off_ot", names)

	def test_every_row_names_its_roster_type(self):
		if not self.data:
			self.skipTest("no attendance in the test range on this instance")
		blank = [r for r in self.data if not r.get("roster_type")]
		self.assertEqual(blank, [], msg=f"{len(blank)} rows carry no roster type")

	def test_day_off_ot_is_a_flag_on_every_row(self):
		if not self.data:
			self.skipTest("no attendance in the test range on this instance")
		for row in self.data:
			self.assertIn(row.get("day_off_ot"), (0, 1), msg=row.get("employee_id"))

	def test_a_filtered_run_only_returns_what_was_asked_for(self):
		# The filter and the column have to agree, or the report says one thing and
		# shows another.
		for roster_type in ("Basic", "Over-Time"):
			rows = execute(_filters(roster_type=roster_type))[1]
			self.assertEqual(
				{r.get("roster_type") for r in rows} - {roster_type}, set(), msg=roster_type
			)

	def test_day_off_ot_filter_returns_only_flagged_rows(self):
		rows = execute(_filters(day_off_ot=1))[1]
		self.assertEqual({r.get("day_off_ot") for r in rows} - {1}, set())


class TestInPageFilters(FrappeTestCase):
	"""Only what changes the query goes to the server. Frappe calls a filter's
	on_change in place of refreshing, so the row-narrowing filters run in the browser
	and no longer queue a background run per keystroke.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "one_fm", "report", "operations_monthly_attendance_sheet",
				"operations_monthly_attendance_sheet.js",
			)
		)

	def test_the_row_narrowing_filters_run_in_page(self):
		for fieldname in ("employee", "employee_status", "employment_type", "roster_type", "day_off_ot"):
			block = self.source.split(f'fieldname: "{fieldname}"')[1].split("},")[0]
			self.assertIn("on_change: apply_in_page_filters", block, msg=fieldname)

	def test_the_filters_that_change_the_query_still_reach_the_server(self):
		# Dates change the range, Include Future Attendance changes the source, and
		# Generate Based On changes what the cells hold - none can be done in page.
		for fieldname in ("from_date", "to_date", "include_future_attendance", "generate_based_on"):
			block = self.source.split(f'fieldname: "{fieldname}"')[1].split("},")[0]
			self.assertNotIn("on_change: apply_in_page_filters", block, msg=fieldname)

	def test_project_stays_on_the_server(self):
		# It narrows the Attendance rows too, not just which employees appear, so an
		# employee with days booked elsewhere would come out differently in page.
		block = self.source.split('fieldname: "project"')[1].split("},")[0]
		self.assertNotIn("on_change: apply_in_page_filters", block)

	def test_the_row_carries_what_the_in_page_filters_match_on(self):
		columns = {c["fieldname"] for c in execute(_filters())[0]}
		for fieldname in ("employee", "employee_status", "employment_type", "roster_type", "day_off_ot"):
			self.assertIn(fieldname, columns, msg=fieldname)

	def test_the_employee_column_holds_the_docname_the_filter_returns(self):
		# The Employee filter returns a docname; the visible Employee ID is the badge
		# number, so matching on that would never hit.
		data = execute(_filters())[1]
		if not data:
			self.skipTest("no attendance in the test range on this instance")
		for row in data[:20]:
			self.assertTrue(frappe.db.exists("Employee", row.get("employee")), msg=row.get("employee"))



class TestTheSummaryBlock(FrappeTestCase):
	"""WI-001979: the columns at the end of a row, and the arithmetic they promise."""

	def test_present_days_counts_only_days_present(self):
		for status in ("Present", "Working", "Work From Home"):
			with self.subTest(status=status):
				self.assertEqual(summary_counter(status), "working_days")

		# What it must NOT absorb - before this the only counters were present and days
		# off, so anything else went uncounted entirely.
		for status in ("Absent", "On Leave", "On Hold", "Holiday"):
			self.assertNotEqual(summary_counter(status), "working_days")

	def test_both_kinds_of_day_off_share_one_column(self):
		self.assertEqual(summary_counter("Day Off"), "off_days")
		self.assertEqual(summary_counter("Client Day Off"), "off_days")

	def test_a_leave_is_counted_under_its_own_type(self):
		self.assertEqual(summary_counter("On Leave", "Annual Leave"), "annual_leave_days")
		self.assertEqual(summary_counter("On Leave", "Sick Leave"), "sick_leave_days")
		self.assertEqual(
			summary_counter("On Leave", "Leave Without Pay"), "leave_without_pay_days"
		)

	def test_a_leave_of_another_type_is_other_not_a_missing_day(self):
		"""Business Trip and Hajj Leave are real leave types on this site."""
		self.assertEqual(summary_counter("On Leave", "Business Trip"), "other_days")
		self.assertEqual(summary_counter("On Leave", None), "other_days")

	def test_a_status_no_column_names_is_other(self):
		# 288 days were On Hold in July 2026; they have to land somewhere.
		self.assertEqual(summary_counter("On Hold"), "other_days")
		self.assertEqual(summary_counter("Holiday"), "other_days")
		self.assertEqual(summary_counter("Client Interview"), "other_days")

	def test_a_day_with_no_status_is_missing(self):
		self.assertEqual(summary_counter(None), "missing_days")
		self.assertEqual(summary_counter(""), "missing_days")

	def test_every_status_lands_on_a_declared_column(self):
		"""A counter this does not declare would vanish from the row silently."""
		statuses = frappe.get_meta("Attendance").get_field("status").options.split("\n")
		for status in statuses + ["Working", "Client Interview", None]:
			self.assertIn(summary_counter(status), SUMMARY_COUNTERS, msg=status)

	def test_the_row_reconciles_to_the_range(self):
		"""The AC's own check: the summary columns add up to the days selected."""
		dates = get_date_range(_filters())
		group = ("Morning", "Basic", 0, "")
		attendance = {
			group: {
				dates[0]: "Present",
				dates[1]: "Absent",
				dates[2]: "On Leave",
				dates[3]: "On Hold",
				# dates[4] deliberately left with no record at all
			}
		}
		day_off = {dates[5]: "Day Off", dates[6]: "Client Day Off"}
		leave_types = {dates[2]: "Sick Leave"}

		rows = get_attendance_status(
			dates, attendance, day_off, {}, {}, employee_leave_types=leave_types
		)

		self.assertEqual(len(rows), 1)
		row = rows[0]
		self.assertEqual(row["working_days"], 1)
		self.assertEqual(row["absent_days"], 1)
		self.assertEqual(row["sick_leave_days"], 1)
		self.assertEqual(row["annual_leave_days"], 0)
		self.assertEqual(row["other_days"], 1)
		self.assertEqual(row["off_days"], 2)
		self.assertEqual(row["missing_days"], 1)
		self.assertEqual(sum(row[counter] for counter in SUMMARY_COUNTERS), len(dates))

	def test_the_row_reconciles_on_real_data(self):
		"""Every row of the busiest month has to add up, not just the constructed one."""
		busiest = frappe.db.sql(
			"""
			select year(attendance_date) as y, month(attendance_date) as mo
			from `tabAttendance` where docstatus = 1
			group by y, mo order by count(*) desc limit 1
			""",
			as_dict=True,
		)
		if not busiest:
			self.skipTest("no submitted attendance on this instance")

		from frappe.utils import get_first_day, get_last_day

		anchor = getdate(f"{busiest[0].y}-{busiest[0].mo:02d}-01")
		lo, hi = get_first_day(anchor), get_last_day(anchor)
		total_days = len(get_date_range(_filters(from_date=lo, to_date=hi)))

		data = execute(_filters(from_date=lo, to_date=hi))[1]
		if not data:
			self.skipTest("no rows for the busiest month")

		for report_row in data[:200]:
			self.assertEqual(
				sum(report_row.get(counter, 0) for counter in SUMMARY_COUNTERS),
				total_days,
				msg=f"{report_row.get('employee_id')}: {[(c, report_row.get(c)) for c in SUMMARY_COUNTERS]}",
			)


class TestAttendanceWithoutAShiftIsStillCounted(FrappeTestCase):
	"""An attendance record with no Operations Shift used to be dropped by an inner join,
	so the day it recorded became a "missing day" and an absence went uncounted. 42,840
	submitted records in 2026 alone have no shift."""

	def setUp(self):
		row = frappe.db.get_value(
			"Attendance",
			{
				"docstatus": 1,
				"operations_shift": ["is", "not set"],
				"status": ["in", ["Absent", "Present", "On Leave"]],
			},
			["employee", "attendance_date", "status", "leave_type"],
			as_dict=True,
			order_by="attendance_date desc",
		)
		if not row:
			self.skipTest("no shift-less attendance on this instance")
		self.record = row

	def test_the_day_it_records_is_not_reported_as_missing(self):
		data = execute(
			_filters(
				from_date=self.record.attendance_date,
				to_date=self.record.attendance_date,
				employee=self.record.employee,
			)
		)[1]

		self.assertTrue(data, msg="the shift-less record produced no row at all")
		self.assertEqual(
			sum(row.get("missing_days", 0) for row in data),
			0,
			msg=f"{self.record} was dropped and counted as a missing day",
		)

	def test_it_lands_in_the_counter_its_status_belongs_to(self):
		data = execute(
			_filters(
				from_date=self.record.attendance_date,
				to_date=self.record.attendance_date,
				employee=self.record.employee,
			)
		)[1]

		# On Leave routes by its leave type, so the expected counter needs both.
		counter = summary_counter(self.record.status, self.record.leave_type)
		self.assertEqual(sum(row.get(counter, 0) for row in data), 1)

	def test_the_query_left_joins_the_shift(self):
		"""Pinned on the SQL: an inner join here silently loses rows rather than failing."""
		from one_fm.one_fm.report.operations_monthly_attendance_sheet.operations_monthly_attendance_sheet import (
			get_non_day_off_attendance_records,
		)
		import inspect

		source = inspect.getsource(get_non_day_off_attendance_records)
		self.assertIn("left_join(OperationsShift)", source)
class TestTheIncludeProjectToggle(FrappeTestCase):
	"""WI-001980: one row per employee, or one row per project they worked on."""

	def _record(self, project):
		return frappe._dict(
			{"shift": "Morning", "roster_type": "Basic", "day_off_ot": 0, "project": project}
		)

	def test_the_project_joins_the_row_key_only_when_asked_for(self):
		a, b = self._record("Project A"), self._record("Project B")

		# Off: two projects, one key - so one row for the employee.
		self.assertEqual(row_group(a), row_group(b))
		# On: a key each.
		self.assertNotEqual(row_group(a, include_project=True), row_group(b, include_project=True))
		self.assertEqual(row_group(a, include_project=True)[3], "Project A")

	def test_the_key_keeps_its_shape_either_way(self):
		"""Everything that unpacks the key reads one shape, whichever way the toggle is."""
		self.assertEqual(len(row_group(self._record("Project A"))), 4)
		self.assertEqual(len(row_group(self._record("Project A"), include_project=True)), 4)

	def test_the_project_column_is_hidden_rather_than_dropped(self):
		"""The client formatter colours by column index and counts hidden columns."""
		off = [c for c in get_columns(_filters(), []) if c["fieldname"] == "project"][0]
		on = [
			c for c in get_columns(_filters(include_project=1), []) if c["fieldname"] == "project"
		][0]

		self.assertTrue(off.get("hidden"))
		self.assertFalse(on.get("hidden"))
		# Same number of columns either way, so the day cells stay under the same indices.
		self.assertEqual(
			len(get_columns(_filters(), [])), len(get_columns(_filters(include_project=1), []))
		)


class TestTheToggleAgainstRealData(FrappeTestCase):
	def setUp(self):
		busiest = frappe.db.sql(
			"""
			select project, year(attendance_date) as y, month(attendance_date) as mo
			from `tabAttendance`
			where docstatus = 1 and project is not null and project != ''
			group by project, y, mo order by count(*) desc limit 1
			""",
			as_dict=True,
		)
		if not busiest:
			self.skipTest("no submitted attendance with a project on this instance")

		from frappe.utils import get_first_day, get_last_day

		anchor = getdate(f"{busiest[0].y}-{busiest[0].mo:02d}-01")
		self.lo, self.hi = get_first_day(anchor), get_last_day(anchor)

	def _rows(self, **extra):
		return execute(_filters(from_date=self.lo, to_date=self.hi, **extra))[1] or []

	def test_including_the_project_never_loses_an_employee(self):
		"""Splitting rows must add rows, not drop people."""
		consolidated = self._rows()
		split = self._rows(include_project=1)
		if not consolidated:
			self.skipTest("no rows for the busiest project month")

		self.assertGreaterEqual(len(split), len(consolidated))
		self.assertEqual({r["employee"] for r in split}, {r["employee"] for r in consolidated})

	def test_a_split_row_carries_the_project_it_is_for(self):
		split = self._rows(include_project=1)
		if not split:
			self.skipTest("no rows for the busiest project month")

		self.assertTrue(any(r.get("project") for r in split))

	def test_each_row_still_reconciles_with_the_project_split_on(self):
		"""WI-001979's arithmetic has to survive the regrouping."""
		split = self._rows(include_project=1)
		if not split:
			self.skipTest("no rows for the busiest project month")

		total_days = len(get_date_range(_filters(from_date=self.lo, to_date=self.hi)))
		for row in split[:200]:
			self.assertEqual(sum(row.get(counter, 0) for counter in SUMMARY_COUNTERS), total_days)

	def test_splitting_by_project_never_loses_a_day_worked(self):
		"""Compared per employee across all their rows, not row to row.

		An employee already gets a row per shift and per Day Off OT flag, so both runs
		return several rows for the same person - the comparison has to be the totals.

		Greater-or-equal rather than equal, and the gap is meaningful: the two runs differ
		only where one date carries attendance under two projects. Consolidated, those
		collapse onto one cell and count once; split, each project counts its own - which
		is what a per-project row is for.
		"""
		consolidated = self._rows()
		split = self._rows(include_project=1)
		if not consolidated:
			self.skipTest("no rows for the busiest project month")

		def present_by_employee(rows):
			totals = {}
			for row in rows:
				totals[row["employee"]] = totals.get(row["employee"], 0) + row.get("working_days", 0)
			return totals

		split_totals = present_by_employee(split)
		for employee, present in present_by_employee(consolidated).items():
			self.assertGreaterEqual(
				split_totals.get(employee, 0),
				present,
				msg=f"{employee} lost present days when split by project",
			)
