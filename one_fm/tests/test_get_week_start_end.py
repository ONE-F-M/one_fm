import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.utils import get_week_start_end


class TestGetWeekStartEnd(FrappeTestCase):
	def test_valid_date(self):
		# 2023-06-14 is a Wednesday.
		# Week starts on Sunday 2023-06-11 and ends on Saturday 2023-06-17.
		result = get_week_start_end("2023-06-14")
		self.assertEqual(result.start, "2023-06-11")
		self.assertEqual(result.end, "2023-06-17")

	def test_invalid_date_raises_validation_error(self):
		with self.assertRaises(frappe.ValidationError):
			get_week_start_end("14-06-2023")

		with self.assertRaises(frappe.ValidationError):
			get_week_start_end("not-a-date")
