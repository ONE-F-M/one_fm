# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings

from one_fm.one_fm.doctype.subcontract_staff_attendance.subcontract_staff_attendance import (
	get_submission_start_day,
	validate_submission_window,
)

SETTING = "subcontractor_attendance_submission_start_day"
MODULE = "one_fm.one_fm.doctype.subcontract_staff_attendance.subcontract_staff_attendance"


def on_date(date_string):
	"""Make the validation see `date_string` as today (freezegun is not installed in the test environment)."""
	return patch(f"{MODULE}.today", return_value=date_string)


class TestSubcontractStaffAttendance(FrappeTestCase):
	def setUp(self):
		# Make sure a valid value is stored so the settings are restored cleanly after each test
		frappe.db.set_single_value("Operation Settings", SETTING, 1)

	@change_settings("Operation Settings", {SETTING: 5})
	def test_throws_day_before_configured_day(self):
		with on_date("2026-02-04"):
			with self.assertRaises(frappe.ValidationError):
				validate_submission_window("2026-01-31")

	@change_settings("Operation Settings", {SETTING: 5})
	def test_message_shows_earliest_date(self):
		with on_date("2026-02-04"):
			with self.assertRaises(frappe.ValidationError) as ctx:
				validate_submission_window("2026-01-31")
		self.assertIn("January 2026", str(ctx.exception))
		self.assertIn(frappe.utils.formatdate("2026-02-05"), str(ctx.exception))

	@change_settings("Operation Settings", {SETTING: 5})
	def test_passes_on_configured_day(self):
		with on_date("2026-02-05"):
			validate_submission_window("2026-01-31")

	@change_settings("Operation Settings", {SETTING: 5})
	def test_passes_after_configured_day(self):
		with on_date("2026-03-20"):
			validate_submission_window("2026-01-31")

	@change_settings("Operation Settings", {SETTING: 1})
	def test_unset_or_zero_falls_back_to_1(self):
		# Bypass the controller validation (which rejects 0) to mimic an existing Single with no value
		frappe.db.set_single_value("Operation Settings", SETTING, 0)
		self.assertEqual(get_submission_start_day(), 1)

		with on_date("2026-01-31"):
			with self.assertRaises(frappe.ValidationError):
				validate_submission_window("2026-01-31")
		with on_date("2026-02-01"):
			validate_submission_window("2026-01-31")

		frappe.db.delete("Singles", {"doctype": "Operation Settings", "field": SETTING})
		frappe.clear_cache(doctype="Operation Settings")
		self.assertEqual(get_submission_start_day(), 1)

	@change_settings("Operation Settings", {SETTING: 10})
	def test_december_to_january_rollover(self):
		with on_date("2027-01-09"):
			with self.assertRaises(frappe.ValidationError):
				validate_submission_window("2026-12-31")
		with on_date("2027-01-10"):
			validate_submission_window("2026-12-31")
