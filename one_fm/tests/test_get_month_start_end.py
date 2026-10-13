import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.utils import get_month_start_end


class TestGetMonthStartEnd(FrappeTestCase):
    def test_valid_date_returns_month_range(self):
        result = get_month_start_end("2024-02-15")
        self.assertEqual(result.start, "2024-02-01")
        self.assertEqual(result.end, "2024-02-29")

    def test_malformed_date_raises_validation_error(self):
        for bad in ("15/02/2024", "not-a-date"):
            with self.subTest(date=bad):
                self.assertRaises(frappe.ValidationError, get_month_start_end, bad)
