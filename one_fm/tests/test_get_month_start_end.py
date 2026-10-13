# Tests for the month range helper get_month_start_end in one_fm/utils.py.
import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.utils import get_month_start_end


class TestGetMonthStartEnd(FrappeTestCase):
	def test_valid_date_returns_month_start_and_end(self):
		# February 2024 is a leap year, so the month ends on the 29th.
		result = get_month_start_end("2024-02-15")
		self.assertEqual(result.start, "2024-02-01")
		self.assertEqual(result.end, "2024-02-29")

	def test_malformed_date_raises_validation_error(self):
		# A date not in YYYY-MM-DD form must raise a clear ValidationError,
		# not a raw ValueError from strptime.
		with self.assertRaises(frappe.ValidationError) as ctx:
			get_month_start_end("15/02/2024")
		self.assertIn("YYYY-MM-DD", str(ctx.exception))
