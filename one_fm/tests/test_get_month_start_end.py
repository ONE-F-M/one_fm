import frappe
from frappe.tests.utils import FrappeTestCase
from one_fm.utils import get_month_start_end


class TestGetMonthStartEnd(FrappeTestCase):
    """Test cases for get_month_start_end function"""

    def test_valid_date_returns_correct_start_and_end(self):
        """Test AC2: Valid dates must return the same start and end as before"""
        # Test with a date in January 2024
        result = get_month_start_end("2024-01-15")
        
        # Verify the result is a dictionary-like object with start and end
        self.assertIsNotNone(result)
        self.assertTrue(hasattr(result, 'start') or isinstance(result, dict))
        
        # Start should be the first day of the month
        self.assertEqual(result.get('start') or result['start'], '2024-01-01')
        
        # End should be the last day of the month (January 31)
        self.assertEqual(result.get('end') or result['end'], '2024-01-31')

    def test_valid_date_february_leap_year(self):
        """Test with February in a leap year"""
        result = get_month_start_end("2024-02-14")
        
        # Start should be February 1st
        self.assertEqual(result.get('start') or result['start'], '2024-02-01')
        
        # End should be February 29th (leap year)
        self.assertEqual(result.get('end') or result['end'], '2024-02-29')

    def test_valid_date_december(self):
        """Test with December (31 days)"""
        result = get_month_start_end("2024-12-25")
        
        # Start should be December 1st
        self.assertEqual(result.get('start') or result['start'], '2024-12-01')
        
        # End should be December 31st
        self.assertEqual(result.get('end') or result['end'], '2024-12-31')

    def test_invalid_date_format_raises_validation_error(self):
        """Test AC3: Invalid date format should raise frappe.ValidationError"""
        # Test with invalid format (DD/MM/YYYY)
        with self.assertRaises(frappe.ValidationError) as context:
            get_month_start_end("15/01/2024")
        
        # Verify the error message mentions the expected format
        error_message = str(context.exception)
        self.assertIn("YYYY-MM-DD", error_message)

    def test_invalid_date_string_raises_validation_error(self):
        """Test AC3: Invalid date string should raise frappe.ValidationError"""
        # Test with completely invalid date
        with self.assertRaises(frappe.ValidationError) as context:
            get_month_start_end("not-a-date")
        
        # Verify the error message mentions the expected format
        error_message = str(context.exception)
        self.assertIn("YYYY-MM-DD", error_message)

    def test_invalid_date_wrong_separator_raises_validation_error(self):
        """Test AC3: Date with wrong separator should raise frappe.ValidationError"""
        # Test with dots instead of dashes
        with self.assertRaises(frappe.ValidationError) as context:
            get_month_start_end("2024.01.15")
        
        # Verify the error message mentions the expected format
        error_message = str(context.exception)
        self.assertIn("YYYY-MM-DD", error_message)

    def test_invalid_date_nonexistent_date_raises_validation_error(self):
        """Test AC3: Non-existent date (e.g., Feb 30) should raise frappe.ValidationError"""
        # Test with invalid date (February 30th doesn't exist)
        with self.assertRaises(frappe.ValidationError) as context:
            get_month_start_end("2024-02-30")
        
        # Verify the error message mentions the expected format
        error_message = str(context.exception)
        self.assertIn("YYYY-MM-DD", error_message)

    def test_valid_date_april(self):
        """Test with April (30 days)"""
        result = get_month_start_end("2023-04-10")
        
        # Start should be April 1st
        self.assertEqual(result.get('start') or result['start'], '2023-04-01')
        
        # End should be April 30th
        self.assertEqual(result.get('end') or result['end'], '2023-04-30')
