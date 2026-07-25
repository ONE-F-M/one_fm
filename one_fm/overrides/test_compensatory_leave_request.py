# Copyright (c) 2026, ONE FM and contributors
# See license.txt

from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from one_fm.overrides.compensatory_leave_request import get_next_working_day

IS_HOLIDAY = "one_fm.overrides.compensatory_leave_request.is_holiday"


class TestCompensatoryLeaveRequestResumptionDate(FrappeTestCase):
	"""
	WI-001696: the auto-generated Leave Application's Resumption Date is the next valid
	working day after the compensatory day off, checked against the employee's Holiday
	List. is_holiday is stubbed so the calendar walk is tested without fixtures.
	"""

	def test_day_after_when_it_is_a_working_day(self):
		with patch(IS_HOLIDAY, return_value=False):
			self.assertEqual(
				get_next_working_day("EMP-TEST-0001", "2026-07-20"), getdate("2026-07-21")
			)

	def test_skips_a_single_holiday(self):
		# 21 Jul is a holiday, 22 Jul is not
		with patch(IS_HOLIDAY, side_effect=lambda employee, date: getdate(date) == getdate("2026-07-21")):
			self.assertEqual(
				get_next_working_day("EMP-TEST-0001", "2026-07-20"), getdate("2026-07-22")
			)

	def test_skips_consecutive_holidays(self):
		holidays = {getdate("2026-07-21"), getdate("2026-07-22"), getdate("2026-07-23")}
		with patch(IS_HOLIDAY, side_effect=lambda employee, date: getdate(date) in holidays):
			self.assertEqual(
				get_next_working_day("EMP-TEST-0001", "2026-07-20"), getdate("2026-07-24")
			)

	def test_accepts_string_or_date_input(self):
		with patch(IS_HOLIDAY, return_value=False):
			self.assertEqual(
				get_next_working_day("EMP-TEST-0001", getdate("2026-07-20")), getdate("2026-07-21")
			)

	def test_lookahead_is_bounded(self):
		# A holiday list that marks every day must not spin forever - it gives up after
		# the lookahead window rather than hanging the Compensatory Leave Request submit.
		with patch(IS_HOLIDAY, return_value=True) as stub:
			result = get_next_working_day("EMP-TEST-0001", "2026-07-20", max_lookahead_days=5)

		self.assertEqual(stub.call_count, 5)
		self.assertEqual(result, getdate("2026-07-26"))
