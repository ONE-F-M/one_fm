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


ITEM_DOCTYPE = "Subcontractor Staff Attendance Item"
EXPECTED_OPTIONS = ["", "Present", "Absent", "Day Off", "Client Day Off"]


class TestSubcontractStaffAttendance(FrappeTestCase):
	def test_day_options_are_only_the_four_statuses(self):
		meta = frappe.get_meta(ITEM_DOCTYPE)
		for fieldname in ("day_1", "day_31"):
			options = meta.get_field(fieldname).options.split("\n")
			self.assertEqual(options, EXPECTED_OPTIONS)

	def test_record_based_on_defaults_to_attendance_status(self):
		meta = frappe.get_meta("Subcontract Staff Attendance")
		self.assertEqual(meta.get_field("attendance_record_based_on").default, "Attendance Status")

	def test_process_audit_logs_counts_only_present_as_working(self):
		doc = frappe.new_doc("Subcontract Staff Attendance")
		# A subcontractor that does not exist: the baseline fetch returns [] (or fails and is ignored)
		doc.subcontractor_name = "_Test Fake Subcontractor"
		doc.from_date = "2026-01-01"
		doc.to_date = "2026-01-31"
		doc.attendance_record_based_on = "Attendance Status"
		doc.append(
			"subcontractor_staff_attendance_item",
			{
				"employee": "_Test Fake Employee",
				"day_1": "Present",
				"day_2": "Absent",
				"day_3": "Day Off",
				"day_4": "Client Day Off",
				"day_5": "Present",
			},
		)

		doc.process_audit_logs()

		row = doc.get("subcontractor_staff_attendance_item")[0]
		self.assertEqual(int(row.working_days), 2)
		self.assertEqual(int(row.off_days), 2)

	def test_removed_status_is_rejected(self):
		doc = frappe.new_doc("Subcontract Staff Attendance")
		row = doc.append(
			"subcontractor_staff_attendance_item",
			{"employee": "_Test Fake Employee", "day_1": "Half Day"},
		)
		with self.assertRaises(frappe.ValidationError):
			row._validate_selects()


class TestSubmissionWindow(FrappeTestCase):
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
		# Store 0 directly to mimic an existing Single with no usable value
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


class TestPortal(FrappeTestCase):
	def test_save_refused_for_another_subcontractor(self):
		from one_fm.one_fm.doctype.subcontract_staff_attendance.subcontract_staff_attendance import save_attendance_records

		with patch("frappe.db.get_value", return_value="Supplier A"), self.assertRaises(frappe.PermissionError):
			save_attendance_records("Supplier B", "2026-01-01", "2026-01-31", "Attendance Status", "[]")

	def test_submit_completes_the_owner_task(self):
		from one_fm.one_fm.doctype.subcontract_staff_attendance.subcontract_staff_attendance import submit_for_review

		task = {"instance_name": "INST-1", "task_id": "T-1", "can_action": True, "task_actions_detail": [{"action": "Submit for Review"}]}
		with patch("frappe.get_all", return_value=["SSA-1"]), \
			patch("processa.api.instances.get_active_bpmn_tasks", return_value=[task]), \
			patch("processa.api.instances.complete_task") as complete_task:
			submit_for_review("Supplier A", "2026-01-01", "2026-01-31")
		complete_task.assert_called_once_with("INST-1", "T-1", frappe.as_json({"action": "Submit for Review"}))

	def test_submit_without_a_task_throws(self):
		from one_fm.one_fm.doctype.subcontract_staff_attendance.subcontract_staff_attendance import submit_for_review

		with patch("frappe.get_all", return_value=["SSA-1"]), \
			patch("processa.api.instances.get_active_bpmn_tasks", return_value=[]), \
			self.assertRaises(frappe.ValidationError):
			submit_for_review("Supplier A", "2026-01-01", "2026-01-31")
