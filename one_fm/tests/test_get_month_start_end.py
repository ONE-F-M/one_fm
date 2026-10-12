import frappe
from frappe.tests.utils import FrappeTestCase
from one_fm.utils import get_month_start_end


class TestGetMonthStartEnd(FrappeTestCase):
    def test_valid_date_returns_correct_month_boundaries(self):
        """Test that a valid date returns the correct start and end of the month"""
        # Test with a date in the middle of January 2024
        result = get_month_start_end('2024-01-15')
        
        # Should return the first and last day of January 2024
        self.assertEqual(result['start'], '2024-01-01')
        self.assertEqual(result['end'], '2024-01-31')
    
    def test_valid_date_february_leap_year(self):
        """Test that a valid date in February of a leap year returns correct boundaries"""
        # Test with a date in February 2024 (leap year)
        result = get_month_start_end('2024-02-15')
        
        # Should return the first and last day of February 2024
        self.assertEqual(result['start'], '2024-02-01')
        self.assertEqual(result['end'], '2024-02-29')
    
    def test_valid_date_december(self):
        """Test that a valid date in December returns correct boundaries"""
        # Test with a date in December 2024
        result = get_month_start_end('2024-12-20')
        
        # Should return the first and last day of December 2024
        self.assertEqual(result['start'], '2024-12-01')
        self.assertEqual(result['end'], '2024-12-31')
    
    def test_invalid_date_format_raises_validation_error(self):
        """Test that an invalid date format raises frappe.ValidationError with a clear message"""
        # Test with malformed date
        with self.assertRaises(frappe.ValidationError) as context:
            get_month_start_end('2024/01/15')
        
        # Verify the error message contains the expected format
        error_message = str(context.exception)
        self.assertIn('YYYY-MM-DD', error_message)
    
    def test_invalid_date_format_empty_string(self):
        """Test that an empty string raises frappe.ValidationError"""
        with self.assertRaises(frappe.ValidationError) as context:
            get_month_start_end('')
        
        error_message = str(context.exception)
        self.assertIn('YYYY-MM-DD', error_message)
    
    def test_invalid_date_format_wrong_order(self):
        """Test that a date in wrong order format raises frappe.ValidationError"""
        with self.assertRaises(frappe.ValidationError) as context:
            get_month_start_end('15-01-2024')
        
        error_message = str(context.exception)
        self.assertIn('YYYY-MM-DD', error_message)
