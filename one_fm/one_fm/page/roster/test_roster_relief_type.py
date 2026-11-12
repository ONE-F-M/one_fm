# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""A Day Off modal reliever's schedule carries the relief type of the covered day."""

from datetime import date
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, get_first_day, get_last_day, getdate, today

from one_fm.one_fm.page.roster.roster import (
	extreme_schedule,
	get_relief_type_flags,
	reliever_roster_assignment,
)
from one_fm.patches.v15_0.backfill_employee_schedule_relief_type import execute as backfill

SEED = "RELIEF-TYPE-SEED-"
MONDAY, FRIDAY = 0, 4
DAY_OFF = {"is_day_off_reliever": 1, "is_weekend_reliever": 0}
WEEKEND = {"is_day_off_reliever": 0, "is_weekend_reliever": 1}


def future_weekday(weekday, offset):
	start = getdate(add_days(today(), offset))
	return add_days(start, (weekday - start.weekday()) % 7)


def seed(suffix, employee, schedule_date, availability="Working", **values):
	frappe.get_doc({
		"doctype": "Employee Schedule",
		"name": SEED + suffix,
		"employee": employee,
		"date": schedule_date,
		"roster_type": "Basic",
		"employee_availability": availability,
		**values,
	}).db_insert()
	return SEED + suffix


def flags(name):
	return frappe.db.get_value(
		"Employee Schedule", name, ["is_day_off_reliever", "is_weekend_reliever"], as_dict=True
	)


class TestGetReliefTypeFlags(FrappeTestCase):
	def test_sunday_to_thursday_is_day_off_relief(self):
		for day in ("2026-11-15", "2026-11-16", "2026-11-19"):
			with self.subTest(day=day):
				self.assertEqual(get_relief_type_flags(day), DAY_OFF)

	def test_friday_and_saturday_are_weekend_relief(self):
		for day in ("2026-11-20", "2026-11-21"):
			with self.subTest(day=day):
				self.assertEqual(get_relief_type_flags(day), WEEKEND)

	def test_accepts_a_date(self):
		self.assertEqual(get_relief_type_flags(date(2026, 11, 20)), WEEKEND)
		self.assertEqual(get_relief_type_flags(date(2026, 11, 16)), DAY_OFF)


class TestReliefTypeThroughTheDayOffModal(FrappeTestCase):
	"""Driven through reliever_roster_assignment, which dayoff() calls with the covered rows."""

	def setUp(self):
		employees = frappe.get_all(
			"Employee",
			filters={"status": "Active", "relieving_date": ["is", "not set"], "date_of_joining": ["is", "set"]},
			pluck="name",
			limit=2,
		)
		if len(employees) < 2:
			self.skipTest("needs two active employees with a joining date and no leaving date")
		self.covered, self.reliever = employees
		self.shift = frappe.db.get_value("Operations Shift", {"status": "Active", "shift_type": ["is", "set"]}, "name")
		self.role = frappe.db.get_value("Operations Role", {}, "name")
		if not (self.shift and self.role):
			self.skipTest("needs an active Operations Shift and an Operations Role")
		for patcher in (patch.object(frappe.db, "commit"), patch("frappe.enqueue")):
			patcher.start()
			self.addCleanup(patcher.stop)
		self.made = []

	def tearDown(self):
		frappe.db.delete("Employee Schedule", {"name": ["like", SEED + "%"]})
		for name in self.made:
			frappe.db.delete("Employee Schedule", {"name": name})

	def _assign(self, day):
		if frappe.db.exists("Employee Schedule", {"employee": ["in", [self.covered, self.reliever]], "date": day}):
			self.skipTest("an employee is already rostered on the test date")
		# reliever_roster_assignment refuses a reliever with no Day Off in the month
		day_off = get_first_day(day) if getdate(day).day != 1 else get_last_day(day)
		seed(f"DO-{day}", self.reliever, day_off, availability="Day Off")
		covered = seed(f"COVERED-{day}", self.covered, day, availability="Day Off")
		reliever_roster_assignment(self.reliever, [{
			"name": covered,
			"date": day,
			"shift": self.shift,
			"operations_role": self.role,
			"start_datetime": f"{day} 08:00:00",
			"end_datetime": f"{day} 16:00:00",
		}])
		name = f"{day}_{self.reliever}_Basic"
		self.made.append(name)
		return name, covered

	def test_a_weekday_reliever_is_flagged_day_off_relief(self):
		name, covered = self._assign(future_weekday(MONDAY, 900))

		row = frappe.db.get_value(
			"Employee Schedule", name, ["is_relieving_schedule", "relieving_employee_schedule"], as_dict=True
		)
		self.assertEqual(row.is_relieving_schedule, 1)
		self.assertEqual(row.relieving_employee_schedule, covered)
		self.assertEqual(flags(name), DAY_OFF)

	def test_a_friday_reliever_is_flagged_weekend_relief(self):
		name, _ = self._assign(future_weekday(FRIDAY, 900))

		self.assertEqual(flags(name), WEEKEND)

	def test_re_rostering_clears_every_relief_flag(self):
		day = future_weekday(MONDAY, 910)
		name, _ = self._assign(day)
		frappe.db.set_value("Employee Schedule", name, {"is_annual_leave_reliever": 1, "leave_application": "HR-LAP-TEST"})

		extreme_schedule(
			employees=[{"employee": self.reliever, "date": str(day)}],
			shift=self.shift,
			operations_role=self.role,
			otRoster="false",
			start_date=str(day),
			end_date=None,
			keep_days_off=0,
			day_off_ot=0,
			employee_list=[self.reliever],
		)

		row = frappe.db.get_value(
			"Employee Schedule",
			name,
			["is_relieving_schedule", "is_day_off_reliever", "is_weekend_reliever", "is_annual_leave_reliever", "leave_application"],
			as_dict=True,
		)
		self.assertEqual(
			row,
			{"is_relieving_schedule": 0, "is_day_off_reliever": 0, "is_weekend_reliever": 0,
				"is_annual_leave_reliever": 0, "leave_application": None},
		)


class TestBackfillReliefType(FrappeTestCase):
	def setUp(self):
		self.employee = frappe.db.get_value("Employee", {"status": "Active"}, "name")
		if not self.employee:
			self.skipTest("no active employee on this site")

	def tearDown(self):
		frappe.db.delete("Employee Schedule", {"name": ["like", SEED + "%"]})

	def test_backfill_classifies_working_relieving_rows_only(self):
		friday = seed("FRI", self.employee, future_weekday(FRIDAY, 920), is_relieving_schedule=1)
		monday = seed("MON", self.employee, future_weekday(MONDAY, 920), is_relieving_schedule=1)
		day_off = seed("OFF", self.employee, future_weekday(FRIDAY, 930), availability="Day Off", is_relieving_schedule=1)
		plain = seed("PLAIN", self.employee, future_weekday(FRIDAY, 940))

		backfill()

		self.assertEqual(flags(friday), WEEKEND)
		self.assertEqual(flags(monday), DAY_OFF)
		self.assertEqual(flags(day_off), {"is_day_off_reliever": 0, "is_weekend_reliever": 0})
		self.assertEqual(flags(plain), {"is_day_off_reliever": 0, "is_weekend_reliever": 0})

		before = {name: flags(name) for name in (friday, monday, day_off, plain)}
		backfill()
		self.assertEqual({name: flags(name) for name in before}, before)
