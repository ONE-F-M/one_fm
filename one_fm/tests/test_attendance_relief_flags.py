# Copyright (c) 2026, ONE FM and contributors
"""Attendance inherits relief flags from its Shift Assignment."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.overrides.attendance import RELIEF_FLAG_FIELDS, set_relief_flags_for_date

DAY_OFF, WEEKEND, ANNUAL = RELIEF_FLAG_FIELDS
TEST_DATE = "2099-02-03"


def make_shift_assignment(name, employee, roster_type="Basic", **flags):
	frappe.get_doc({
		"doctype": "Shift Assignment",
		"name": name,
		"employee": employee,
		"start_date": TEST_DATE,
		"roster_type": roster_type,
		"status": "Active",
		"docstatus": 1,
		**flags,
	}).db_insert()
	return name


def make_attendance(name, employee, shift_assignment=None, roster_type="Basic", status="Present"):
	"""Insert without the controller (as the raw inserts do); return the in-memory doc."""
	attendance = frappe.get_doc({
		"doctype": "Attendance",
		"name": name,
		"employee": employee,
		"attendance_date": TEST_DATE,
		"roster_type": roster_type,
		"shift_assignment": shift_assignment,
		"status": status,
		"docstatus": 1,
	})
	attendance.db_insert()
	return attendance


def get_flags(attendance_name):
	return frappe.db.get_value("Attendance", attendance_name, list(RELIEF_FLAG_FIELDS), as_dict=True)


class TestAttendanceAfterInsert(FrappeTestCase):
	def test_present_on_flagged_shift_assignment_sets_flag(self):
		sa = make_shift_assignment("_T-RLF-SA-P", "_T-RLF-P", **{ANNUAL: 1})
		make_attendance("_T-RLF-ATT-P", "_T-RLF-P", sa).after_insert()
		self.assertEqual(get_flags("_T-RLF-ATT-P"), {DAY_OFF: 0, WEEKEND: 0, ANNUAL: 1})

	def test_absent_keeps_flag_after_switch_to_on_leave(self):
		sa = make_shift_assignment("_T-RLF-SA-A", "_T-RLF-A", **{WEEKEND: 1})
		make_attendance("_T-RLF-ATT-A", "_T-RLF-A", sa, status="Absent").after_insert()
		# The leave application path changes status with set_value on the same row
		frappe.db.set_value("Attendance", "_T-RLF-ATT-A", "status", "On Leave")
		self.assertEqual(get_flags("_T-RLF-ATT-A")[WEEKEND], 1)

	def test_double_shift_flags_only_the_relief_attendance(self):
		basic = make_shift_assignment("_T-RLF-SA-B", "_T-RLF-D")
		overtime = make_shift_assignment("_T-RLF-SA-OT", "_T-RLF-D", "Over-Time", **{DAY_OFF: 1})
		make_attendance("_T-RLF-ATT-B", "_T-RLF-D", basic).after_insert()
		make_attendance("_T-RLF-ATT-OT", "_T-RLF-D", overtime, "Over-Time").after_insert()
		self.assertEqual(get_flags("_T-RLF-ATT-B")[DAY_OFF], 0)
		self.assertEqual(get_flags("_T-RLF-ATT-OT")[DAY_OFF], 1)

	def test_unlinked_attendance_finds_shift_assignment_by_roster_type(self):
		make_shift_assignment("_T-RLF-SA-LB", "_T-RLF-L")
		make_shift_assignment("_T-RLF-SA-LOT", "_T-RLF-L", "Over-Time", **{DAY_OFF: 1})
		make_attendance("_T-RLF-ATT-LOT", "_T-RLF-L", roster_type="Over-Time").after_insert()
		self.assertEqual(get_flags("_T-RLF-ATT-LOT")[DAY_OFF], 1)

	def test_unflagged_shift_assignment_writes_nothing(self):
		sa = make_shift_assignment("_T-RLF-SA-N", "_T-RLF-N")
		attendance = make_attendance("_T-RLF-ATT-N", "_T-RLF-N", sa)
		with patch.object(attendance, "db_set") as db_set:
			attendance.set_relief_flags()
		db_set.assert_not_called()


class TestReliefFlagsForDate(FrappeTestCase):
	def test_raw_inserted_attendance_inherits_flags(self):
		flagged = make_shift_assignment("_T-RLF-SA-R1", "_T-RLF-R1", **{WEEKEND: 1})
		plain = make_shift_assignment("_T-RLF-SA-R2", "_T-RLF-R2")
		make_attendance("_T-RLF-ATT-R1", "_T-RLF-R1", flagged)
		make_attendance("_T-RLF-ATT-R2", "_T-RLF-R2", plain)
		set_relief_flags_for_date(TEST_DATE)
		self.assertEqual(get_flags("_T-RLF-ATT-R1"), {DAY_OFF: 0, WEEKEND: 1, ANNUAL: 0})
		self.assertEqual(get_flags("_T-RLF-ATT-R2"), {DAY_OFF: 0, WEEKEND: 0, ANNUAL: 0})
