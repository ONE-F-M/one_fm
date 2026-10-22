# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, now_datetime


class TestBoardingTimeStamp(FrappeTestCase):
	"""WI-003682: stamp_boarding_time() on Transportation Manifest."""

	def _doc(self, *statuses, boarding_time=None):
		doc = frappe.new_doc("Transportation Manifest")
		for i, status in enumerate(statuses, start=1):
			row = doc.append(
				"transportation_manifest_details",
				{"stop_name": "Stop", "attendance_status": status, "boarding_time": boarding_time},
			)
			row.name = f"row-{i}"
		return doc

	def _before(self, *statuses, boarding_time=None):
		return self._doc(*statuses, boarding_time=boarding_time)

	def test_field_is_read_only_datetime_after_attendance_status(self):
		meta = frappe.get_meta("Transportation Manifest Details")
		field = meta.get_field("boarding_time")
		self.assertEqual(field.fieldtype, "Datetime")
		self.assertEqual(field.label, "Boarding Time")
		self.assertEqual(field.read_only, 1)
		order = [f.fieldname for f in meta.fields]
		self.assertEqual(order.index("boarding_time"), order.index("attendance_status") + 1)

	def test_new_document_present_row_is_stamped(self):
		doc = self._doc("Present", "Absent", None)
		with patch.object(type(doc), "get_doc_before_save", return_value=None):
			doc.stamp_boarding_time()
		rows = doc.transportation_manifest_details
		self.assertIsNotNone(rows[0].boarding_time)
		self.assertIsNone(rows[1].boarding_time)
		self.assertIsNone(rows[2].boarding_time)

	def test_becoming_present_stamps_and_staying_present_keeps_time(self):
		earlier = add_to_date(now_datetime(), hours=-2)
		doc = self._doc("Present", "Present")
		doc.transportation_manifest_details[1].boarding_time = earlier
		before = self._before("Absent", "Present", boarding_time=earlier)
		before.transportation_manifest_details[0].boarding_time = None
		with patch.object(type(doc), "get_doc_before_save", return_value=before):
			doc.stamp_boarding_time()
		rows = doc.transportation_manifest_details
		self.assertIsNotNone(rows[0].boarding_time)
		self.assertEqual(rows[1].boarding_time, earlier)

	def test_leaving_present_clears_time(self):
		stamp = now_datetime()
		doc = self._doc("Absent", None, boarding_time=stamp)
		before = self._before("Present", "Present", boarding_time=stamp)
		with patch.object(type(doc), "get_doc_before_save", return_value=before):
			doc.stamp_boarding_time()
		for row in doc.transportation_manifest_details:
			self.assertIsNone(row.boarding_time)

	def test_validate_calls_stamp_after_attendance_validation(self):
		calls = []
		doc = self._doc("Present")
		names = (
			"populate_shift_details_from_schedule",
			"populate_stop_sequence_and_pickup_accommodation",
			"enforce_stop_locking",
			"validate_attendance_and_qoa",
			"stamp_boarding_time",
			"validate_relievers",
		)
		patches = [
			patch.object(type(doc), name, lambda self, n=name: calls.append(n)) for name in names
		]
		for p in patches:
			p.start()
		try:
			doc.validate()
		finally:
			for p in patches:
				p.stop()
		self.assertEqual(calls.index("stamp_boarding_time"), calls.index("validate_attendance_and_qoa") + 1)
