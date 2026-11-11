# Copyright (c) 2023, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings


class TestOperationSettings(FrappeTestCase):
	def _save_start_day(self, value):
		settings = frappe.get_doc("Operation Settings")
		settings.subcontractor_attendance_submission_start_day = value
		settings.save()

	def test_start_day_zero_throws(self):
		with self.assertRaises(frappe.ValidationError):
			self._save_start_day(0)

	def test_start_day_above_28_throws(self):
		with self.assertRaises(frappe.ValidationError):
			self._save_start_day(29)

	@change_settings("Operation Settings", {"subcontractor_attendance_submission_start_day": 5})
	def test_start_day_1_saves(self):
		self._save_start_day(1)
		self.assertEqual(
			frappe.db.get_single_value("Operation Settings", "subcontractor_attendance_submission_start_day"), 1
		)

	@change_settings("Operation Settings", {"subcontractor_attendance_submission_start_day": 5})
	def test_start_day_28_saves(self):
		self._save_start_day(28)
		self.assertEqual(
			frappe.db.get_single_value("Operation Settings", "subcontractor_attendance_submission_start_day"), 28
		)
