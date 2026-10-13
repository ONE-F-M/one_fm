import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.utils import get_month_start_end


class TestGetMonthStartEnd(FrappeTestCase):
    def test_valid_mid_month_date(self):
        result = get_month_start_end("2024-03-15")
        self.assertEqual(result.start, "2024-03-01")
        self.assertEqual(result.end, "2024-03-31")

    def test_valid_leap_february(self):
        result = get_month_start_end("2024-02-10")
        self.assertEqual(result.start, "2024-02-01")
        self.assertEqual(result.end, "2024-02-29")

    def test_valid_december(self):
        result = get_month_start_end("2023-12-31")
        self.assertEqual(result.start, "2023-12-01")
        self.assertEqual(result.end, "2023-12-31")

    def test_invalid_date_raises_validation_error(self):
        for bad in ("15-03-2024", "2024/03/15", "not a date", "2024-13-01", ""):
            with self.assertRaises(frappe.ValidationError) as ctx:
                get_month_start_end(bad)
            self.assertIn("YYYY-MM-DD", str(ctx.exception))
