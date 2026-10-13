from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

MODULE = "one_fm.overrides.employee_checkin"
RELIEVING_DATE = "2026-10-10"


def make_checkin(time, log_type="IN"):
	checkin = frappe.new_doc("Employee Checkin")
	checkin.employee = "HR-EMP-TEST"
	checkin.log_type = log_type
	checkin.time = time
	return checkin


class TestCheckinAfterRelievingDate(FrappeTestCase):
	def check(self, time, relieving_date=RELIEVING_DATE, log_type="IN"):
		checkin = make_checkin(time, log_type)
		with patch(f"{MODULE}.frappe.db.get_value", return_value=relieving_date):
			checkin.validate_not_after_relieving_date()

	def test_allows_checkout_the_morning_after_an_overnight_last_shift(self):
		self.check("2026-10-11 06:00:00", log_type="OUT")

	def test_blocks_checkin_the_day_after_the_relieving_date(self):
		with self.assertRaises(frappe.ValidationError) as context:
			self.check("2026-10-11 07:55:00")
		self.assertIn("you cannot check in after it", str(context.exception))

	def test_allows_checkin_on_the_relieving_date(self):
		self.check("2026-10-10 18:30:00")

	def test_allows_checkin_before_the_relieving_date(self):
		self.check("2026-10-09 07:55:00")

	def test_allows_checkin_without_a_relieving_date(self):
		self.check("2026-10-11 07:55:00", relieving_date=None)

	def test_validate_shows_the_message_not_a_traceback(self):
		checkin = make_checkin("2026-10-11 07:55:00")
		with (
			patch(f"{MODULE}.frappe.db.get_value", return_value=RELIEVING_DATE),
			patch(f"{MODULE}.frappe.get_cached_value", return_value="Active"),
		):
			with self.assertRaises(frappe.ValidationError) as context:
				checkin.validate()
		self.assertIn("you cannot check in after it", str(context.exception))
		self.assertNotIn("Traceback", str(context.exception))
