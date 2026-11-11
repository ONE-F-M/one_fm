# Copyright (c) 2026, ONE FM and contributors
"""Attendance inherits relief flags from its Shift Assignment (WI-004454).

The Shift Assignment relief fields come from WI-004455 / WI-004451, so the controller
tests stand the Shift Assignment lookup in with mocks rather than depending on them.
"""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.custom.custom_field.attendance import get_attendance_custom_fields
from one_fm.overrides import attendance as attendance_module
from one_fm.overrides.attendance import (
	RELIEF_FLAG_FIELDS,
	AttendanceOverride,
	get_relief_flag_update_query,
)

DAY_OFF, WEEKEND, ANNUAL = RELIEF_FLAG_FIELDS


class FakeAttendance:
	"""Just enough of an Attendance for set_relief_flags: db_set writes to a dict."""

	def __init__(self, shift_assignment="SA-1", roster_type="Basic", status="Present"):
		self.employee = "EMP-1"
		self.attendance_date = "2026-11-11"
		self.roster_type = roster_type
		self.shift_assignment = shift_assignment
		self.row = {"status": status}
		self.writes = []

	def db_set(self, field, value=None):
		self.writes.append(field)
		if isinstance(field, dict):
			self.row.update(field)
		else:
			self.row[field] = value

	set_relief_flags = AttendanceOverride.set_relief_flags


def _run(attendance, sa_values, lookup=None):
	def get_value(doctype, filters, fieldname=None, as_dict=False):
		if isinstance(filters, dict):
			return lookup
		return sa_values.get(filters)

	with patch.object(attendance_module, "get_relief_flag_fields", return_value=list(RELIEF_FLAG_FIELDS)), \
		patch.object(attendance_module.frappe.db, "get_value", side_effect=get_value):
		attendance.set_relief_flags()
	return attendance


class TestReliefFieldDefinitions(FrappeTestCase):
	def setUp(self):
		self.fields = {f["fieldname"]: f for f in get_attendance_custom_fields()["Attendance"]}

	def test_the_three_flags_are_read_only_checks(self):
		for name in RELIEF_FLAG_FIELDS:
			self.assertEqual(self.fields[name]["fieldtype"], "Check")
			self.assertEqual(self.fields[name]["read_only"], 1)

	def test_section_and_breaks_follow_the_ba_layout(self):
		self.assertEqual(self.fields["custom_reliever_details"]["fieldtype"], "Section Break")
		self.assertEqual(self.fields["custom_reliever_details"]["insert_after"], "day_off_ot")
		self.assertEqual(self.fields[DAY_OFF]["insert_after"], "custom_reliever_details")
		self.assertEqual(self.fields["custom_column_break_78jcz"]["insert_after"], DAY_OFF)
		self.assertEqual(self.fields[WEEKEND]["insert_after"], "custom_column_break_78jcz")
		self.assertEqual(self.fields["custom_column_break_jl7kq"]["insert_after"], WEEKEND)
		self.assertEqual(self.fields[ANNUAL]["insert_after"], "custom_column_break_jl7kq")

	def test_no_leave_link_or_event_staff_is_added(self):
		self.assertNotIn("custom_event_staff", self.fields)

	def test_patch_is_registered_in_post_model_sync(self):
		with open(frappe.get_app_path("one_fm", "patches.txt")) as f:
			text = f.read()
		self.assertIn("one_fm.patches.v15_0.add_attendance_relief_fields", text.split("[post_model_sync]")[1])


class TestSetReliefFlags(FrappeTestCase):
	def test_present_on_flagged_shift_assignment_sets_flag(self):
		att = _run(FakeAttendance(), {"SA-1": {DAY_OFF: 1, WEEKEND: 0, ANNUAL: 0}})
		self.assertEqual(att.row[DAY_OFF], 1)
		self.assertNotIn(WEEKEND, att.row)

	def test_absent_with_no_checkin_still_gets_flag(self):
		att = _run(FakeAttendance(status="Absent"), {"SA-1": {DAY_OFF: 0, WEEKEND: 1, ANNUAL: 0}})
		self.assertEqual(att.row[WEEKEND], 1)

	def test_annual_leave_flag(self):
		att = _run(FakeAttendance(), {"SA-1": {DAY_OFF: 0, WEEKEND: 0, ANNUAL: 1}})
		self.assertEqual(att.row[ANNUAL], 1)

	def test_flag_survives_the_switch_to_on_leave(self):
		att = _run(FakeAttendance(), {"SA-1": {DAY_OFF: 1, WEEKEND: 0, ANNUAL: 0}})
		att.db_set("status", "On Leave")  # what the leave application path does
		self.assertEqual(att.row["status"], "On Leave")
		self.assertEqual(att.row[DAY_OFF], 1)

	def test_double_shift_only_the_relief_attendance_is_flagged(self):
		sa = {
			"SA-BASIC": {DAY_OFF: 0, WEEKEND: 0, ANNUAL: 0},
			"SA-OT": {DAY_OFF: 1, WEEKEND: 0, ANNUAL: 0},
		}
		basic = _run(FakeAttendance("SA-BASIC", "Basic"), sa)
		overtime = _run(FakeAttendance("SA-OT", "Over-Time"), sa)
		self.assertNotIn(DAY_OFF, basic.row)
		self.assertEqual(overtime.row[DAY_OFF], 1)

	def test_unflagged_shift_assignment_writes_nothing(self):
		att = _run(FakeAttendance(), {"SA-1": {DAY_OFF: 0, WEEKEND: 0, ANNUAL: 0}})
		self.assertEqual(att.writes, [])

	def test_without_shift_assignment_link_it_is_found_by_employee_date_and_roster(self):
		att = _run(
			FakeAttendance(shift_assignment=None, roster_type="Over-Time"),
			{"SA-OT": {DAY_OFF: 1, WEEKEND: 0, ANNUAL: 0}},
			lookup="SA-OT",
		)
		self.assertEqual(att.row[DAY_OFF], 1)

	def test_nothing_to_inherit_when_no_shift_assignment_exists(self):
		att = _run(FakeAttendance(shift_assignment=None), {}, lookup=None)
		self.assertEqual(att.writes, [])

	def test_no_write_when_shift_assignment_has_no_relief_fields_yet(self):
		att = FakeAttendance()
		with patch.object(attendance_module, "get_relief_flag_fields", return_value=[]):
			att.set_relief_flags()
		self.assertEqual(att.writes, [])


class TestReliefFlagBulkUpdate(FrappeTestCase):
	def test_query_joins_shift_assignment_and_sets_the_flags(self):
		sql = str(get_relief_flag_update_query("2026-11-11", list(RELIEF_FLAG_FIELDS)))
		self.assertIn("JOIN", sql)
		self.assertIn("tabShift Assignment", sql)
		for name in RELIEF_FLAG_FIELDS:
			self.assertIn(name, sql)
		self.assertIn("2026-11-11", sql)
		self.assertIn("SET", sql)
