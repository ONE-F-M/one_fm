# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

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
