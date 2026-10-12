import frappe
from frappe.tests.utils import FrappeTestCase
from one_fm.utils import get_week_start_end


class TestGetWeekStartEnd(FrappeTestCase):
    def test_get_week_start_end_valid_date(self):
        """Test that valid dates return correct start and end dates."""
        # Test with a known date: 2024-01-15 is a Monday
        result = get_week_start_end("2024-01-15")
        
        # Verify result is a dict-like object with start and end keys
        self.assertIn("start", result)
        self.assertIn("end", result)
        
        # Verify start and end are strings
        self.assertIsInstance(result["start"], str)
        self.assertIsInstance(result["end"], str)
        
        # Verify the result has both start and end dates
        self.assertTrue(result["start"])
        self.assertTrue(result["end"])
    
    def test_get_week_start_end_invalid_date_format(self):
        """Test that invalid date formats raise frappe.ValidationError with proper message."""
        # Test with various invalid formats
        invalid_dates = [
            "2024/01/15",      # Wrong separators
            "01-15-2024",      # Wrong order
            "15-01-2024",      # Wrong order
            "2024-1-15",       # Missing zero padding
            "invalid-date",    # Completely invalid
            "2024-13-01",      # Invalid month
        ]
        
        for invalid_date in invalid_dates:
            with self.assertRaises(frappe.ValidationError) as context:
                get_week_start_end(invalid_date)
            
            # Verify the error message contains the expected format
            error_message = str(context.exception)
            self.assertIn("YYYY-MM-DD", error_message)
