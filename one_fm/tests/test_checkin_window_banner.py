# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for the check-in window banner (WI-001777).

The banner quotes the window the Shift Type actually configures - check-in opens at
`start - begin_check_in_before_shift_start_time` and is blocked from
`start + working_hours_threshold_for_absent`, with `late_entry_grace_period` only
flagging lateness. It is consulted on the path that previously ended at the
unhelpful "You are not assigned to a shift".
"""

from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_datetime, getdate

from one_fm.api.v1.face_recognition import (
	_fmt_clock,
	get_checkin_window_message,
	get_checkin_windows,
	get_site_location,
)
from one_fm.overrides.employee import NOT_RETURNED_FROM_LEAVE


def _window(start, opens_before=60, late_grace=15, absent_after=4.0):
	start = get_datetime(start)
	return frappe._dict(
		shift_assignment="TEST-SA",
		start=start,
		opens_at=start - timedelta(minutes=opens_before),
		late_after=start + timedelta(minutes=late_grace),
		blocked_after=start + timedelta(hours=absent_after),
	)


class TestClockFormat(FrappeTestCase):
	def test_it_reads_like_the_banner(self):
		self.assertEqual(_fmt_clock(get_datetime("2026-07-30 09:00:00")), "9:00 AM")
		self.assertEqual(_fmt_clock(get_datetime("2026-07-30 14:30:00")), "2:30 PM")
		self.assertEqual(_fmt_clock(get_datetime("2026-07-30 00:05:00")), "12:05 AM")


class TestWindowMessage(FrappeTestCase):
	"""The four states, driven off constructed windows so the clock is deterministic."""

	def _message_at(self, now, windows):
		with patch(
			"one_fm.api.v1.face_recognition.get_checkin_windows", return_value=windows
		), patch(
			"one_fm.api.v1.face_recognition.now_datetime", return_value=get_datetime(now)
		):
			return get_checkin_window_message("EMP-TEST")

	def test_no_shift_today_says_nothing(self):
		# Leaves the existing day-off / holiday / leave messages to speak.
		self.assertEqual(self._message_at("2026-07-30 10:00:00", []), "")

	def test_before_the_window_opens_quotes_the_opening_time(self):
		# 15:00 shift, opens 14:00. At 10:00 it has not opened.
		msg = self._message_at("2026-07-30 10:00:00", [_window("2026-07-30 15:00:00")])
		self.assertIn("Check-In Unavailable", msg)
		self.assertIn("3:00 PM", msg)
		self.assertIn("2:00 PM", msg)

	def test_after_the_window_closes_quotes_the_closing_time(self):
		# 08:00 shift blocked from 12:00 (4h). At 13:00 it has closed.
		msg = self._message_at("2026-07-30 13:00:00", [_window("2026-07-30 08:00:00")])
		self.assertIn("Check-In Window Closed", msg)
		self.assertIn("12:00 PM", msg)
		self.assertIn("Site Supervisor", msg)

	def test_back_to_back_shifts_name_the_closed_one_and_the_next_opening(self):
		# The AC's fifth scenario: morning window gone, next not yet open.
		msg = self._message_at(
			"2026-07-30 13:00:00",
			[_window("2026-07-30 08:00:00"), _window("2026-07-30 15:00:00")],
		)
		self.assertIn("Check-In Window Closed", msg)
		self.assertIn("8:00 AM", msg)   # which shift closed
		self.assertIn("12:00 PM", msg)  # when it closed
		self.assertIn("2:00 PM", msg)   # when the next one opens

	def test_a_window_that_is_open_produces_no_banner(self):
		# 08:00 shift, open 07:00-12:00. At 09:00 check-in is allowed, so the caller
		# never reaches the banner and there is nothing to say.
		self.assertEqual(
			self._message_at("2026-07-30 09:00:00", [_window("2026-07-30 08:00:00")]), ""
		)

	def test_the_grace_period_does_not_close_the_window(self):
		# 15 minutes past start only flags lateness; check-in is still allowed.
		self.assertEqual(
			self._message_at("2026-07-30 08:30:00", [_window("2026-07-30 08:00:00")]), ""
		)


class TestWindowsFromShiftType(FrappeTestCase):
	"""Boundaries must come from the Shift Type, not an assumed hour."""

	def test_boundaries_derive_from_the_configured_fields(self):
		row = frappe.db.sql(
			"""
			select sa.employee, sa.start_datetime,
			       st.begin_check_in_before_shift_start_time as opens_before,
			       st.late_entry_grace_period as late_grace,
			       st.working_hours_threshold_for_absent as absent_after
			from `tabShift Assignment` sa
			join `tabShift Type` st on st.name = sa.shift_type
			where sa.docstatus = 1 and sa.status = 'Active'
			  and sa.start_datetime is not null
			order by sa.start_datetime desc limit 1
			""",
			as_dict=True,
		)
		if not row:
			self.skipTest("no submitted Shift Assignment on this instance")
		row = row[0]

		with patch(
			"one_fm.api.v1.face_recognition.getdate",
			return_value=getdate(row.start_datetime),
		):
			windows = get_checkin_windows(row.employee)

		match = [w for w in windows if w.start == row.start_datetime]
		if not match:
			self.skipTest("the sampled assignment is not on its own start date")
		w = match[0]
		self.assertEqual(w.opens_at, row.start_datetime - timedelta(minutes=row.opens_before))
		self.assertEqual(w.late_after, row.start_datetime + timedelta(minutes=row.late_grace))
		self.assertEqual(
			w.blocked_after, row.start_datetime + timedelta(hours=row.absent_after)
		)

	def test_an_employee_with_no_assignment_today_has_no_windows(self):
		self.assertEqual(get_checkin_windows("_no_such_employee"), [])


class TestNotReturnedFromLeaveBlocker(FrappeTestCase):
	"""The status blocker takes priority over any shift window (AC 3)."""

	def test_the_status_is_spelled_the_way_employee_stores_it(self):
		# The comparison used to read "Not Returned From Leave", which no Employee ever
		# holds, so the blocker never fired and the API talked about shift windows
		# instead. The Select option is the authority.
		options = frappe.get_meta("Employee").get_field("status").options.split("\n")
		self.assertIn(NOT_RETURNED_FROM_LEAVE, options)

	def test_the_source_compares_against_that_constant(self):
		for path in (
			("one_fm", "api", "v1", "face_recognition.py"),
			("one_fm", "overrides", "employee_checkin.py"),
		):
			source = frappe.read_file(frappe.get_app_path(*path))
			self.assertNotIn("Not Returned From Leave", source, msg=path[-1])
			self.assertIn("NOT_RETURNED_FROM_LEAVE", source, msg=path[-1])

	def test_the_blocked_employee_is_told_what_to_do(self):
		employee = frappe.db.get_value(
			"Employee", {"status": NOT_RETURNED_FROM_LEAVE}, ["name", "employee_id"], as_dict=True
		)
		if not employee or not employee.employee_id:
			self.skipTest("no employee is currently marked as not returned from leave")

		# Coordinates only have to be present - the status is checked before they matter.
		get_site_location(
			employee_id=employee.employee_id, latitude=29.3759, longitude=47.9774
		)

		# response() puts the sentence the app shows in the "error" slot; "message" is
		# the coarse label. The banner reads the sentence.
		banner = frappe.local.response.get("error") or ""
		self.assertEqual(frappe.local.response.get("status_code"), 403)
		self.assertIn("Action Required", banner)
		self.assertIn("Duty Resumption", banner)
		# It must not fall through to a shift-window message the status makes moot.
		self.assertNotIn("Check-In Window", banner)
