# Copyright (c) 2026, ONE FM and contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from one_fm.overrides.compensatory_leave_request import (
	CompensatoryLeaveRequestOverride,
	get_next_working_day,
)

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


class TestCompensatoryLeaveRequestOverrideShape(FrappeTestCase):
	def test_every_method_stays_on_the_class(self):
		"""
		Regression guard for a real break: get_next_working_day was inserted at module
		level *between* two methods, which silently turned everything below it into a
		nested function instead of a method. The file still compiled, so the only symptom
		was AttributeError: no attribute 'create_leave_allocation_without_period', raised
		mid-flow from "Verify Attendance" after the attendance had already been submitted.
		"""
		for method in (
			"on_submit",
			"create_draft_leave_application",
			"create_leave_allocation_without_period",
			"get_existing_allocation",  # inherited from HRMS
		):
			self.assertTrue(
				callable(getattr(CompensatoryLeaveRequestOverride, method, None)),
				msg=f"{method} is not a method on the override class",
			)

	def test_helper_stays_at_module_level(self):
		# The counterpart: it must not drift back inside the class.
		self.assertFalse(hasattr(CompensatoryLeaveRequestOverride, "get_next_working_day"))
		self.assertTrue(callable(get_next_working_day))

	def test_override_is_the_class_frappe_resolves(self):
		# If the doctype ever went custom, the override would stop loading entirely.
		doc = frappe.get_doc({"doctype": "Compensatory Leave Request"})
		self.assertEqual(doc.__class__.__name__, "CompensatoryLeaveRequestOverride")
