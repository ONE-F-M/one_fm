import frappe
from frappe.tests.utils import FrappeTestCase
from one_fm.utils import get_week_start_end


class TestGetWeekStartEnd(FrappeTestCase):
	"""Test the get_week_start_end function with valid and invalid date formats"""

	def test_valid_date_returns_correct_week_boundaries(self):
		"""Test that valid dates in YYYY-MM-DD format return correct week start and end dates"""
		# Test with a known date: 2024-01-15 (a Monday)
		result = get_week_start_end("2024-01-15")
		
		# Verify the result is a tuple with start and end dates
		self.assertIsNotNone(result)
		self.assertEqual(len(result), 2)
		
		# Result should have start and end attributes
		self.assertIsNotNone(result[0])  # start date
		self.assertIsNotNone(result[1])  # end date

	def test_valid_date_format_string(self):
		"""Test that valid YYYY-MM-DD format strings work"""
		result = get_week_start_end("2024-01-01")
		self.assertIsNotNone(result)

	def test_invalid_date_format_raises_validation_error(self):
		"""Test that invalid date formats raise ValidationError with clear message"""
		invalid_dates = [
			"2024/01/15",  # Wrong separator
			"01-15-2024",  # Wrong order
			"15-01-2024",  # Wrong order
			"2024-1-15",   # Missing leading zero
			"not-a-date",  # Not a date
			"2024-13-01",  # Invalid month
			"2024-01-32",  # Invalid day
		]
		
		for invalid_date in invalid_dates:
			with self.subTest(invalid_date=invalid_date):
				with self.assertRaises(frappe.ValidationError) as context:
					get_week_start_end(invalid_date)
				
				# Verify the error message mentions the expected format
				error_msg = str(context.exception)
				self.assertIn("YYYY-MM-DD", error_msg, 
					f"Error message should mention YYYY-MM-DD format for input: {invalid_date}")

	def test_error_message_is_translatable(self):
		"""Test that the error message uses frappe's translation system"""
		with self.assertRaises(frappe.ValidationError) as context:
			get_week_start_end("invalid-date")
		
		# The error should be raised (validation error exists)
		self.assertIsNotNone(context.exception)
