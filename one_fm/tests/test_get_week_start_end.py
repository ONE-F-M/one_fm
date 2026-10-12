import frappe
from frappe.tests.utils import FrappeTestCase
from one_fm.utils import get_week_start_end


class TestGetWeekStartEnd(FrappeTestCase):
	"""Test the get_week_start_end function with valid and invalid date formats"""

	def test_valid_date_returns_correct_week_boundaries(self):
		"""Test that valid dates in YYYY-MM-DD format return correct week start and end dates"""
		# Test with a known date: 2024-01-15 (a Monday)
		result = get_week_start_end("2024-01-15")
		
		# Verify the result has start and end attributes
		self.assertTrue(hasattr(result, 'start'), "Result should have 'start' attribute")
		self.assertTrue(hasattr(result, 'end'), "Result should have 'end' attribute")
		
		# Verify both start and end dates are not None
		self.assertIsNotNone(result.start)
		self.assertIsNotNone(result.end)

	def test_valid_date_format_string(self):
		"""Test that valid YYYY-MM-DD format strings work"""
		result = get_week_start_end("2024-01-01")
		self.assertIsNotNone(result)
		self.assertTrue(hasattr(result, 'start'))
		self.assertTrue(hasattr(result, 'end'))

	def test_invalid_date_format_raises_validation_error(self):
		"""Test that invalid date formats raise ValidationError with clear message"""
		# Test formats that definitely won't parse as YYYY-MM-DD
		invalid_dates = [
			"2024/01/15",  # Wrong separator (/ instead of -)
			"01-15-2024",  # Wrong order
			"15-01-2024",  # Wrong order  
			"not-a-date",  # Not a date at all
			"2024-13-01",  # Invalid month
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
		# The message should mention the format
		self.assertIn("YYYY-MM-DD", str(context.exception))
