# Copyright (c) 2021, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestOvertimeRequest(FrappeTestCase):
	def _make_doc(self, overtime_type, overtime_hours, **kwargs):
		"""Build an in-memory Overtime Request (not saved) for logic testing."""
		doc = frappe.new_doc("Overtime Request")
		doc.overtime_type = overtime_type
		doc.overtime_hours = overtime_hours
		for key, value in kwargs.items():
			doc.set(key, value)
		return doc

	def test_eligible_on_public_holiday_with_9_hours(self):
		# AC 1: Public Holiday + hours >= 9 -> eligible
		doc = self._make_doc("Overtime on Public Holiday", 9)
		doc.set_compensatory_day_off_eligibility()
		self.assertEqual(doc.eligible_for_compensatory_day_off, 1)

	def test_eligible_on_public_holiday_above_9_hours(self):
		# AC 1 (boundary above): Public Holiday + hours > 9 -> eligible
		doc = self._make_doc("Overtime on Public Holiday", 12.5)
		doc.set_compensatory_day_off_eligibility()
		self.assertEqual(doc.eligible_for_compensatory_day_off, 1)

	def test_not_eligible_public_holiday_below_9_hours(self):
		# AC 3: Public Holiday but hours < 9 -> not eligible, day off cleared
		doc = self._make_doc(
			"Overtime on Public Holiday", 8.99, compensatory_day_off="2026-07-20"
		)
		doc.set_compensatory_day_off_eligibility()
		self.assertEqual(doc.eligible_for_compensatory_day_off, 0)
		self.assertIsNone(doc.compensatory_day_off)

	def test_not_eligible_other_type_regardless_of_hours(self):
		# AC 2: Any other type -> not eligible even with high hours
		for overtime_type in ("Overtime after Working Hours", "Overtime on Day Off"):
			doc = self._make_doc(overtime_type, 20)
			doc.set_compensatory_day_off_eligibility()
			self.assertEqual(
				doc.eligible_for_compensatory_day_off,
				0,
				msg=f"{overtime_type} should never be eligible",
			)

	def test_type_change_resets_flag_and_clears_day_off(self):
		# AC 4: Was eligible with a day off, type changes away -> reset + clear
		doc = self._make_doc(
			"Overtime on Public Holiday",
			10,
			eligible_for_compensatory_day_off=1,
			compensatory_day_off="2026-07-20",
		)
		doc.overtime_type = "Overtime after Working Hours"
		doc.set_compensatory_day_off_eligibility()
		self.assertEqual(doc.eligible_for_compensatory_day_off, 0)
		self.assertIsNone(doc.compensatory_day_off)
