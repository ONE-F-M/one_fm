import frappe
import unittest
from datetime import datetime, timedelta
from frappe.tests.utils import FrappeTestCase
from one_fm.utils import get_week_start_end


class TestGetWeekStartEnd(FrappeTestCase):
    def test_valid_date_handling(self):
        """Test that valid dates return correct start and end"""
        # Test with a known date: 2024-01-15 (a Monday)
        result = get_week_start_end('2024-01-15')
        
        # Should return a dict with start and end dates
        self.assertIsNotNone(result)
        self.assertIn('start', result)
        self.assertIn('end', result)
        
        # Verify the result is a valid date string in YYYY-MM-DD format
        start_date = datetime.strptime(result['start'], '%Y-%m-%d')
        end_date = datetime.strptime(result['end'], '%Y-%m-%d')
        
        # End date should be 6 days after start
        expected_diff = timedelta(days=6)
        self.assertEqual(end_date - start_date, expected_diff)
    
    def test_invalid_date_format_raises_validation_error(self):
        """Test that invalid date format raises frappe.ValidationError"""
        # Test with invalid formats
        invalid_dates = [
            '01-15-2024',  # MM-DD-YYYY
            '2024/01/15',  # YYYY/MM/DD
            '15-01-2024',  # DD-MM-YYYY
            '2024-13-01',  # Invalid month
            'not-a-date',  # Random string
            '2024-01-32',  # Invalid day
        ]
        
        for invalid_date in invalid_dates:
            with self.assertRaises(frappe.ValidationError) as context:
                get_week_start_end(invalid_date)
            
            # Check that the error message mentions the expected format
            error_message = str(context.exception)
            self.assertIn('YYYY-MM-DD', error_message)
    
    def test_valid_date_returns_consistent_result(self):
        """Test that valid dates return consistent results"""
        # Test the same date multiple times
        date_str = '2024-06-15'
        result1 = get_week_start_end(date_str)
        result2 = get_week_start_end(date_str)
        
        # Results should be identical
        self.assertEqual(result1['start'], result2['start'])
        self.assertEqual(result1['end'], result2['end'])
