# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-004065 - the Staff Roster View marks relief shifts on the server.

is_relief_shift() classifies one Employee Schedule row; CreateMap.process_records() puts the
flag on schedule records and lets attendance records inherit it from their matched schedule.
"""

import pandas as pd
from frappe.tests.utils import FrappeTestCase

from one_fm.one_fm.page.roster.employee_map import CreateMap, is_relief_shift

MONDAY = "2026-09-07"
FRIDAY = "2026-09-11"
SATURDAY = "2026-09-12"


def make_schedule(**overrides):
	schedule = {
		"employee_availability": "Working",
		"shift": "Home Shift",
		"actual_shift": "Home Shift",
		"date": MONDAY,
		"is_rambo_schedule": 0,
		"is_relieving_schedule": 0,
		"active_rambo_assignment": None,
		"custom_is_reliever": 0,
		"custom_is_weekend_reliever": 0,
	}
	schedule.update(overrides)
	return schedule


class TestIsReliefShift(FrappeTestCase):
	def test_base_is_not_relief(self):
		self.assertEqual(is_relief_shift(make_schedule()), 0)

	def test_active_rambo_assignment(self):
		self.assertEqual(is_relief_shift(make_schedule(is_rambo_schedule=1, active_rambo_assignment="RA-1")), 1)

	def test_rambo_flag_without_active_assignment(self):
		self.assertEqual(is_relief_shift(make_schedule(is_rambo_schedule=1)), 0)

	def test_relieving_schedule_on_home_shift(self):
		self.assertEqual(is_relief_shift(make_schedule(is_relieving_schedule=1)), 1)

	def test_relieving_schedule_on_day_off_row(self):
		row = make_schedule(is_relieving_schedule=1, employee_availability="Day Off")
		self.assertEqual(is_relief_shift(row), 0)
		row["employee_availability"] = "Client Day Off"
		self.assertEqual(is_relief_shift(row), 0)

	def test_rambo_on_day_off_row(self):
		row = make_schedule(active_rambo_assignment="RA-1", employee_availability="Day Off")
		self.assertEqual(is_relief_shift(row), 0)

	def test_day_off_reliever(self):
		self.assertEqual(is_relief_shift(make_schedule(custom_is_reliever=1)), 0)
		self.assertEqual(is_relief_shift(make_schedule(custom_is_reliever=1, shift="Other Shift")), 1)

	def test_weekend_reliever(self):
		off_home = {"custom_is_weekend_reliever": 1, "shift": "Other Shift"}
		self.assertEqual(is_relief_shift(make_schedule(**off_home)), 0)
		self.assertEqual(is_relief_shift(make_schedule(date=FRIDAY, **off_home)), 1)
		self.assertEqual(is_relief_shift(make_schedule(date=SATURDAY, **off_home)), 1)
		self.assertEqual(is_relief_shift(make_schedule(date=FRIDAY, custom_is_weekend_reliever=1)), 0)

	def test_rambo_reliever_alone_flags_nothing(self):
		row = make_schedule(shift="Other Shift", custom_is_rambo_reliever=1)
		self.assertEqual(is_relief_shift(row), 0)

	def test_none_and_empty_flags(self):
		for empty in (None, ""):
			row = make_schedule(
				shift="Other Shift",
				date=FRIDAY,
				is_rambo_schedule=empty,
				is_relieving_schedule=empty,
				active_rambo_assignment=empty,
				custom_is_reliever=empty,
				custom_is_weekend_reliever=empty,
			)
			with self.subTest(empty=empty):
				self.assertEqual(is_relief_shift(row), 0)


class TestProcessRecordsReliefFlag(FrappeTestCase):
	def build_map(self, with_attendance):
		cm = object.__new__(CreateMap)
		cm.date_range = pd.date_range(start=MONDAY, end=MONDAY)
		cm.employee_period_details = {}
		cm.formated_rs = {}
		cm.employee_records_raw = [
			{
				"name": "EMP-RELIEF-1",
				"employee_id": "RELIEF-1",
				"relieving_date": None,
				"employee_name": "Relief Tester",
				"day_off_category": None,
				"number_of_days_off": None,
				"custom_is_rambo_reliever": 0,
			}
		]
		base = {
			"employee": "EMP-RELIEF-1",
			"employee_name": "Relief Tester",
			"date": MONDAY,
			"operations_role": None,
			"post_abbrv": None,
			"shift": "Home Shift",
			"start_datetime": None,
			"end_datetime": None,
			"employee_availability": "Working",
			"day_off_ot": 0,
			"is_rambo_schedule": 0,
			"is_relieving_schedule": 0,
			"active_rambo_assignment": None,
			"actual_shift": "Home Shift",
			"custom_is_reliever": 0,
			"custom_is_weekend_reliever": 0,
		}
		cm.schedule_records_raw = [
			dict(base, roster_type="Basic", is_relieving_schedule=1),
			dict(base, roster_type="Over-Time"),
		]
		cm.attendance_records_raw = []
		if with_attendance:
			att = {
				"employee": "EMP-RELIEF-1",
				"employee_name": "Relief Tester",
				"attendance_date": MONDAY,
				"leave_application": None,
				"leave_type": None,
				"operations_shift": "Home Shift",
				"start_time": None,
				"end_time": None,
				"day_off_ot": 0,
				"actual_shift": "Home Shift",
			}
			cm.attendance_records_raw = [
				dict(att, status="Present", roster_type="Basic"),
				dict(att, status="Absent", roster_type="Over-Time"),
			]
		cm.build_employee_details()
		cm.process_records()
		return cm.formated_rs["Relief Tester"][MONDAY]

	def test_attendance_inherits_relief_flag(self):
		records = self.build_map(with_attendance=True)
		by_type = {r["roster_type"]: r for r in records}
		self.assertEqual(by_type["Basic"]["attendance"], "Present")
		self.assertEqual(by_type["Basic"]["is_relief_shift"], 1)
		self.assertEqual(by_type["Over-Time"]["attendance"], "Absent")
		self.assertEqual(by_type["Over-Time"]["is_relief_shift"], 0)

	def test_schedule_records_carry_relief_flag(self):
		records = self.build_map(with_attendance=False)
		by_type = {r["roster_type"]: r for r in records}
		self.assertEqual(by_type["Basic"]["is_relief_shift"], 1)
		self.assertEqual(by_type["Over-Time"]["is_relief_shift"], 0)


class TestScheduleQuery(FrappeTestCase):
	def test_schedule_query_runs_and_selects_rambo_assignment(self):
		import frappe

		cm = object.__new__(CreateMap)
		cm.str_filter = "1 = 0"
		cm.employees = "('NO-SUCH-EMPLOYEE')"
		query = cm.schedule_query()
		self.assertIn("active_rambo_assignment", query)

		# emp.project / emp.site are columns the query already selected before this change; a
		# test site without them cannot run any roster query, so do not blame this change.
		for column in ("project", "site", "shift"):
			if not frappe.db.has_column("Employee", column):
				self.skipTest(f"Employee.{column} is missing on this site; the roster query cannot run")

		self.assertEqual(frappe.db.sql(query, as_dict=1), [])
