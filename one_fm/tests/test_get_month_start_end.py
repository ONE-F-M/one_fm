import frappe
from frappe.tests.utils import FrappeTestCase
from one_fm.utils import get_month_start_end


class TestGetMonthStartEnd(FrappeTestCase):
    """Test suite for get_month_start_end function"""

    def test_valid_date_january(self):
        """Test that valid date returns correct start and end dates for January"""
        result = get_month_start_end('2024-01-15')
        self.assertEqual(result.start, '2024-01-01', "Start date should be first day of month")
        self.assertEqual(result.end, '2024-01-31', "End date should be last day of month")

    def test_valid_date_february_leap_year(self):
        """Test that valid date returns correct start and end dates for February in leap year"""
        result = get_month_start_end('2024-02-10')
        self.assertEqual(result.start, '2024-02-01', "Start date should be first day of month")
        self.assertEqual(result.end, '2024-02-29', "End date should be last day of February in leap year")

    def test_valid_date_february_non_leap_year(self):
        """Test that valid date returns correct start and end dates for February in non-leap year"""
        result = get_month_start_end('2023-02-10')
        self.assertEqual(result.start, '2023-02-01', "Start date should be first day of month")
        self.assertEqual(result.end, '2023-02-28', "End date should be last day of February in non-leap year")

    def test_valid_date_december(self):
        """Test that valid date returns correct start and end dates for December"""
        result = get_month_start_end('2024-12-25')
        self.assertEqual(result.start, '2024-12-01', "Start date should be first day of month")
        self.assertEqual(result.end, '2024-12-31', "End date should be last day of month")

    def test_invalid_date_format_wrong_order(self):
        """Test that invalid date format (wrong order) raises ValidationError"""
        with self.assertRaises(frappe.ValidationError) as cm:
            get_month_start_end('01-15-2024')
        
        # Check that the error message contains the expected format
        error_message = str(cm.exception)
        self.assertIn('YYYY-MM-DD', error_message, 
                      "Error message should mention the expected YYYY-MM-DD format")

    def test_invalid_date_format_text(self):
        """Test that invalid date format (text) raises ValidationError"""
        with self.assertRaises(frappe.ValidationError) as cm:
            get_month_start_end('invalid-date')
        
        # Check that the error message contains the expected format
        error_message = str(cm.exception)
        self.assertIn('YYYY-MM-DD', error_message, 
                      "Error message should mention the expected YYYY-MM-DD format")

    def test_invalid_date_format_wrong_separator(self):
        """Test that invalid date format (wrong separator) raises ValidationError"""
        with self.assertRaises(frappe.ValidationError) as cm:
            get_month_start_end('2024/01/15')
        
        # Check that the error message contains the expected format
        error_message = str(cm.exception)
        self.assertIn('YYYY-MM-DD', error_message, 
                      "Error message should mention the expected YYYY-MM-DD format")

    def test_invalid_date_format_empty_string(self):
        """Test that empty string raises ValidationError"""
        with self.assertRaises(frappe.ValidationError) as cm:
            get_month_start_end('')
        
        # Check that the error message contains the expected format
        error_message = str(cm.exception)
        self.assertIn('YYYY-MM-DD', error_message, 
                      "Error message should mention the expected YYYY-MM-DD format")

    def test_valid_date_first_day_of_month(self):
        """Test that first day of month returns correct start and end"""
        result = get_month_start_end('2024-05-01')
        self.assertEqual(result.start, '2024-05-01', "Start date should be first day of month")
        self.assertEqual(result.end, '2024-05-31', "End date should be last day of month")

    def test_valid_date_last_day_of_month(self):
        """Test that last day of month returns correct start and end"""
        result = get_month_start_end('2024-06-30')
        self.assertEqual(result.start, '2024-06-01', "Start date should be first day of month")
        self.assertEqual(result.end, '2024-06-30', "End date should be last day of month")
