# Copyright (c) 2021, ONE FM and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

BALANCE_SOURCE = (
	"one_fm.one_fm.doctype.overtime_request.overtime_request.get_unredeemed_balance"
)


class TestOvertimeRequest(FrappeTestCase):
	def _make_doc(self, overtime_type, overtime_hours, **kwargs):
		"""Build an in-memory Overtime Request (not saved) for logic testing."""
		doc = frappe.new_doc("Overtime Request")
		doc.overtime_type = overtime_type
		doc.overtime_hours = overtime_hours
		for key, value in kwargs.items():
			doc.set(key, value)
		return doc

	def _balance_for(self, overtime_hours, prior_balance, **kwargs):
		"""
		Run the cumulative balance calculation with a stubbed prior balance.

		The prior balance is what the employee's other requests already carry; stubbing it
		keeps these tests on the arithmetic and threshold rules (the part WI-001695 adds)
		without having to satisfy every Overtime Request validation to save fixtures.
		"""
		kwargs.setdefault("workflow_state", "Pending Line Manager")
		kwargs.setdefault("employee", "EMP-TEST-0001")
		doc = self._make_doc("Overtime on Public Holiday", overtime_hours, **kwargs)

		with patch(BALANCE_SOURCE, return_value=prior_balance):
			doc.set_cumulative_unredeemed_balance()

		doc.set_compensatory_day_off_eligibility()
		return doc

	# ------------------------------------------------------------------
	# WI-001695 - cumulative public holiday overtime balance
	# ------------------------------------------------------------------

	def test_first_public_holiday_overtime_accrues(self):
		# AC1: 0 unredeemed, 3 hours submitted -> balance 3, no prompt
		doc = self._balance_for(3, prior_balance=0)
		self.assertEqual(doc.cumulative_unredemmed_balance, 3)
		self.assertEqual(doc.eligible_for_compensatory_day_off, 0)

	def test_balance_below_threshold_routes_normally(self):
		# AC2: 3 already unredeemed + 4 more = 7 -> still under 9, no prompt
		doc = self._balance_for(4, prior_balance=3)
		self.assertEqual(doc.cumulative_unredemmed_balance, 7)
		self.assertEqual(doc.eligible_for_compensatory_day_off, 0)

	def test_balance_crossing_threshold_triggers_prompt(self):
		# AC3: 7 already unredeemed + 3 more = 10 -> eligible, date now required
		doc = self._balance_for(3, prior_balance=7)
		self.assertEqual(doc.cumulative_unredemmed_balance, 10)
		self.assertEqual(doc.eligible_for_compensatory_day_off, 1)

	def test_threshold_is_inclusive(self):
		# Exactly 9 cumulative hours earns the day off
		doc = self._balance_for(2, prior_balance=7)
		self.assertEqual(doc.cumulative_unredemmed_balance, 9)
		self.assertEqual(doc.eligible_for_compensatory_day_off, 1)

	def test_fractional_hours_accumulate_exactly(self):
		# Why the field is a Float and not an Int: two 4.5-hour holidays reach the
		# threshold. Truncating to whole hours would stall at 8 and never trigger.
		doc = self._balance_for(4.5, prior_balance=4.5)
		self.assertEqual(doc.cumulative_unredemmed_balance, 9)
		self.assertEqual(doc.eligible_for_compensatory_day_off, 1)

	def test_redeemed_request_gives_back_nine_hours(self):
		# AC4: a request that raised a Compensatory Leave Request keeps the remainder
		# (7 + 3 = 10, minus the 9 redeemed = 1) and stays eligible for the record.
		doc = self._balance_for(3, prior_balance=7, compensatory_leave_request="CLR-TEST-0001")
		self.assertEqual(doc.cumulative_unredemmed_balance, 1)
		self.assertEqual(doc.eligible_for_compensatory_day_off, 1)

	def test_draft_counts_its_own_hours(self):
		"""
		A Draft must evaluate its own hours, or the Compensatory Day Off field is hidden
		while the employee is filling the request in and any date they pick is wiped on
		save - the client counts them, so the server has to as well.
		"""
		doc = self._balance_for(10, prior_balance=0, workflow_state="Draft")
		self.assertEqual(doc.cumulative_unredemmed_balance, 10)
		self.assertEqual(doc.eligible_for_compensatory_day_off, 1)

	def test_draft_never_accrues_into_another_request(self):
		# The anti-inflation rule lives in the query behind get_unredeemed_balance: an
		# abandoned draft must not raise a false prompt on the employee's next request.
		from one_fm.one_fm.doctype.overtime_request.overtime_request import (
			ACCRUING_WORKFLOW_STATES,
		)

		self.assertNotIn("Draft", ACCRUING_WORKFLOW_STATES)
		self.assertNotIn("Rejected", ACCRUING_WORKFLOW_STATES)
		self.assertNotIn("Cancelled", ACCRUING_WORKFLOW_STATES)

	def test_remainder_carries_into_the_next_request(self):
		# The reported case: a 9.75-hour holiday already redeemed leaves 0.75, and a new
		# 12-hour holiday must be eligible on 12.75 - not hidden because it is a Draft.
		doc = self._balance_for(12, prior_balance=0.75, workflow_state="Draft")
		self.assertEqual(doc.cumulative_unredemmed_balance, 12.75)
		self.assertEqual(doc.eligible_for_compensatory_day_off, 1)

	def test_non_public_holiday_overtime_carries_no_balance(self):
		# Only public holiday overtime accrues; other types store 0 and never prompt.
		for overtime_type in ("Overtime after Working Hours", "Overtime on Day Off"):
			doc = self._make_doc(
				overtime_type, 20, employee="EMP-TEST-0001", workflow_state="Pending Line Manager"
			)
			with patch(BALANCE_SOURCE, return_value=50) as stub:
				doc.set_cumulative_unredeemed_balance()

			doc.set_compensatory_day_off_eligibility()
			self.assertEqual(doc.cumulative_unredemmed_balance, 0, msg=overtime_type)
			self.assertEqual(doc.eligible_for_compensatory_day_off, 0, msg=overtime_type)
			stub.assert_not_called()

	def test_high_hours_alone_no_longer_grant_eligibility(self):
		# The rule is cumulative, not per request: 12 hours on a public holiday is not
		# eligible on its own if the employee's unredeemed balance was already spent.
		doc = self._make_doc(
			"Overtime on Public Holiday", 12, cumulative_unredemmed_balance=2
		)
		doc.set_compensatory_day_off_eligibility()
		self.assertEqual(doc.eligible_for_compensatory_day_off, 0)

	def test_below_threshold_clears_selected_day_off(self):
		# Balance under 9 -> not eligible, and any selected day off is cleared
		doc = self._make_doc(
			"Overtime on Public Holiday",
			8.99,
			cumulative_unredemmed_balance=8.99,
			compensatory_day_off="2026-07-20",
		)
		doc.set_compensatory_day_off_eligibility()
		self.assertEqual(doc.eligible_for_compensatory_day_off, 0)
		self.assertIsNone(doc.compensatory_day_off)

	def test_not_eligible_other_type_regardless_of_hours(self):
		# AC 2: Any other type -> not eligible even with high hours
		for overtime_type in ("Overtime after Working Hours", "Overtime on Day Off"):
			doc = self._make_doc(overtime_type, 20)
			doc.set_compensatory_day_off_eligibility()
			self.assertEqual(
				doc.eligible_for_compensatory_day_off,
				0,
				msg=f"{overtime_type} should never be eligible",
			)

	def test_type_change_resets_flag_and_clears_day_off(self):
		# AC 4: Was eligible with a day off, type changes away -> reset + clear
		doc = self._make_doc(
			"Overtime on Public Holiday",
			10,
			eligible_for_compensatory_day_off=1,
			compensatory_day_off="2026-07-20",
		)
		doc.overtime_type = "Overtime after Working Hours"
		doc.set_compensatory_day_off_eligibility()
		self.assertEqual(doc.eligible_for_compensatory_day_off, 0)
		self.assertIsNone(doc.compensatory_day_off)

	def test_day_off_required_once_employee_accepts(self):
		# AC2: eligible, no Compensatory Day Off, employee has accepted
		# (Pending Line Manager onward) -> blocked until a date is added.
		for state in (
			"Pending Line Manager",
			"Pending Payroll Officer",
			"Pending Finance Manager",
			"Completed",
		):
			doc = self._make_doc(
				"Overtime on Public Holiday",
				10,
				date="2026-07-13",
				eligible_for_compensatory_day_off=1,
				workflow_state=state,
			)
			with self.assertRaises(frappe.ValidationError, msg=f"state {state} should require a date"):
				doc.validate_compensatory_day_off()

	def test_day_off_optional_when_line_manager_routes(self):
		# AC1: LM creates an eligible request and routes it to the employee
		# without a Compensatory Day Off -> allowed (date filled by employee later).
		for state in ("Draft", "Pending Acceptance by Employee"):
			doc = self._make_doc(
				"Overtime on Public Holiday",
				10,
				date="2026-07-13",
				eligible_for_compensatory_day_off=1,
				workflow_state=state,
			)
			# Should not raise
			doc.validate_compensatory_day_off()

	def test_line_manager_prefilled_date_still_window_validated(self):
		# AC1: even at the routing stage, a pre-filled out-of-window date is blocked.
		doc = self._make_doc(
			"Overtime on Public Holiday",
			10,
			date="2026-07-13",
			eligible_for_compensatory_day_off=1,
			workflow_state="Pending Acceptance by Employee",
			compensatory_day_off="2026-07-25",
		)
		with self.assertRaises(frappe.ValidationError):
			doc.validate_compensatory_day_off()

	def test_day_off_within_window_accepted(self):
		# AC: eligible with a day off inside the 7-day window -> accepted
		doc = self._make_doc(
			"Overtime on Public Holiday",
			10,
			date="2026-07-13",
			eligible_for_compensatory_day_off=1,
			compensatory_day_off="2026-07-16",
		)
		# Should not raise
		doc.validate_compensatory_day_off()

	def test_day_off_window_boundaries_accepted(self):
		# AC: overtime date (day 0) and overtime date + 7 (day 7) are inclusive
		for comp_off in ("2026-07-13", "2026-07-20"):
			doc = self._make_doc(
				"Overtime on Public Holiday",
				10,
				date="2026-07-13",
				eligible_for_compensatory_day_off=1,
				compensatory_day_off=comp_off,
			)
			# Should not raise
			doc.validate_compensatory_day_off()

	def test_day_off_beyond_window_blocked(self):
		# AC: day 8 (2026-07-21) is outside the window -> blocked
		doc = self._make_doc(
			"Overtime on Public Holiday",
			10,
			date="2026-07-13",
			eligible_for_compensatory_day_off=1,
			compensatory_day_off="2026-07-21",
		)
		with self.assertRaises(frappe.ValidationError):
			doc.validate_compensatory_day_off()

	def test_day_off_before_overtime_date_blocked(self):
		# AC: a date before the overtime date is outside the window -> blocked
		doc = self._make_doc(
			"Overtime on Public Holiday",
			10,
			date="2026-07-13",
			eligible_for_compensatory_day_off=1,
			compensatory_day_off="2026-07-12",
		)
		with self.assertRaises(frappe.ValidationError):
			doc.validate_compensatory_day_off()

	def test_validation_skipped_when_not_eligible(self):
		# Not eligible -> validation is a no-op even with no day off
		doc = self._make_doc(
			"Overtime after Working Hours",
			10,
			date="2026-07-13",
			eligible_for_compensatory_day_off=0,
		)
		# Should not raise
		doc.validate_compensatory_day_off()

	# --- Compensatory Leave Request auto-creation guards ---
	# These exercise the early-return guards in create_compensatory_leave_request
	# without touching the database. The DB reuse/create path is covered by the
	# workflow integration behaviour.

	def _clr_doc(self, **kwargs):
		"""Build an eligible, Completed, Present request ready for CLR creation."""
		defaults = dict(
			date="2026-07-13",
			workflow_state="Completed",
			eligible_for_compensatory_day_off=1,
			present=1,
			compensatory_day_off="2026-07-16",
			compensatory_leave_request=None,
		)
		defaults.update(kwargs)
		doc = self._make_doc("Overtime on Public Holiday", 10, **defaults)
		# has_value_changed reads from the loaded (_doc_before_save) snapshot;
		# a brand-new in-memory doc reports every field as changed, which is
		# what we want for these guard tests.
		return doc

	def test_clr_skipped_when_not_completed(self):
		# Not in Completed state -> no CLR attempt, link stays empty
		doc = self._clr_doc(workflow_state="Pending Finance Manager")
		doc.create_compensatory_leave_request()
		self.assertFalse(doc.compensatory_leave_request)

	def test_clr_skipped_when_not_eligible(self):
		# Completed but not eligible -> no CLR
		doc = self._clr_doc(eligible_for_compensatory_day_off=0)
		doc.create_compensatory_leave_request()
		self.assertFalse(doc.compensatory_leave_request)

	def test_clr_skipped_when_absent(self):
		# Completed + eligible but employee was Absent -> no comp leave
		doc = self._clr_doc(present=0, absent=1)
		doc.create_compensatory_leave_request()
		self.assertFalse(doc.compensatory_leave_request)

	def test_clr_skipped_when_no_day_off_date(self):
		# Completed + eligible + present but no Compensatory Day Off date -> skip
		doc = self._clr_doc(compensatory_day_off=None)
		doc.create_compensatory_leave_request()
		self.assertFalse(doc.compensatory_leave_request)

	def test_clr_skipped_when_already_linked(self):
		# Already linked -> no duplicate work
		doc = self._clr_doc(compensatory_leave_request="HR-CMP-EXISTING")
		doc.create_compensatory_leave_request()
		self.assertEqual(doc.compensatory_leave_request, "HR-CMP-EXISTING")
