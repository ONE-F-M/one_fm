# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002604: what the requestor is told once their DSOT request has been decided."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import formatdate

from one_fm.operations.doctype.employee_schedule import dsot_notification
from one_fm.operations.doctype.employee_schedule.dsot_notification import (
	ACTIVE,
	DECIDED_STATES,
	OUTCOME_FLAG,
	REJECTED,
	SYSTEM_PROCESSOR,
	format_cycles,
	processed_by,
	queue_outcome,
	schedule_list_url,
)


def _row(date, state, modified_by="m.mothaffar@one-fm.com"):
	return frappe._dict(
		name=f"ES-{date}",
		employee="HR-EMP-04448",
		employee_name="Dilli Bahadur Khapangi",
		date=date,
		site="Landmark Group - Head Office",
		owner="s.supervisor@one-fm.com",
		workflow_state=state,
		modified_by=modified_by,
	)


class TestTheDateBlocks(FrappeTestCase):
	def test_a_fully_approved_range_reads_as_one_block(self):
		"""AC1: 10-20 Sep approved, nothing rejected."""
		dates = [f"2026-09-{day:02d}" for day in range(10, 21)]
		self.assertEqual(
			format_cycles(dates),
			f"{formatdate('2026-09-10')} - {formatdate('2026-09-20')}",
		)

	def test_an_empty_side_says_so_rather_than_leaving_a_blank(self):
		"""AC1 and AC2: "None (0 shifts)", not a cell the reader has to interpret."""
		self.assertEqual(format_cycles([]), "None (0 shifts)")

	def test_a_single_day_is_that_day(self):
		self.assertEqual(format_cycles(["2026-09-15"]), formatdate("2026-09-15"))

	def test_a_split_range_reads_as_two_blocks(self):
		"""AC3: 15 Sep rejected out of 10-20 leaves 10-14 and 16-20 approved."""
		approved = [f"2026-09-{day:02d}" for day in list(range(10, 15)) + list(range(16, 21))]
		self.assertEqual(
			format_cycles(approved),
			f"{formatdate('2026-09-10')} - {formatdate('2026-09-14')}, "
			f"{formatdate('2026-09-16')} - {formatdate('2026-09-20')}",
		)

	def test_the_rejected_side_of_the_same_split_is_the_one_day(self):
		self.assertEqual(format_cycles(["2026-09-15"]), formatdate("2026-09-15"))

	def test_two_shifts_on_one_day_are_still_one_day(self):
		self.assertEqual(
			format_cycles(["2026-09-15", "2026-09-15"]), formatdate("2026-09-15")
		)


class TestWhoProcessedIt(FrappeTestCase):
	def test_an_approver_is_named(self):
		decided = [_row("2026-09-10", ACTIVE, modified_by="m.mothaffar@one-fm.com")]
		self.assertNotIn("auto-expired", processed_by(decided))
		self.assertTrue(processed_by(decided))

	def test_a_part_expired_request_names_the_person_who_did_decide(self):
		"""Half a range answered and half left to expire still had a real approver."""
		decided = [
			_row("2026-09-10", ACTIVE, modified_by="m.mothaffar@one-fm.com"),
			_row("2026-09-11", REJECTED, modified_by=SYSTEM_PROCESSOR),
		]
		self.assertNotIn("auto-expired", processed_by(decided))

	def test_an_expired_request_says_nobody_answered_it(self):
		"""AC2: the hourly job closes it under Administrator, and the email should not
		name a person who never saw it."""
		decided = [_row("2026-09-10", REJECTED, modified_by=SYSTEM_PROCESSOR)]
		self.assertEqual(processed_by(decided), "System Administrator (auto-expired)")

	def test_a_request_with_no_actor_at_all_reads_as_auto_expired(self):
		decided = [_row("2026-09-10", REJECTED, modified_by=None)]
		self.assertEqual(processed_by(decided), "System Administrator (auto-expired)")


class TestTheLink(FrappeTestCase):
	def test_it_spans_the_whole_request_not_one_side_of_it(self):
		"""The point of the link is to see the approved and rejected days together."""
		url = schedule_list_url("HR-EMP-04448", ["2026-09-20", "2026-09-10", "2026-09-15"])
		self.assertIn("employee=HR-EMP-04448", url)
		self.assertIn("2026-09-10", url)
		self.assertIn("2026-09-20", url)

	def test_it_does_not_filter_on_a_state(self):
		url = schedule_list_url("HR-EMP-04448", ["2026-09-10"])
		self.assertNotIn("workflow_state", url)


class TestTheQueue(FrappeTestCase):
	def tearDown(self):
		frappe.flags.pop(OUTCOME_FLAG, None)

	def test_it_holds_names_until_the_transaction_commits(self):
		"""A range is only knowable once every row in it has been decided."""
		queue_outcome(["ES-0001", "ES-0002"])
		self.assertEqual(frappe.flags[OUTCOME_FLAG], {"ES-0001", "ES-0002"})

	def test_it_is_separate_from_the_approval_queue(self):
		"""One roster run can hold new requests and decide old ones; the two emails go to
		different people about different shifts."""
		self.assertNotEqual(OUTCOME_FLAG, dsot_notification.FLAG)

	def test_nothing_queued_registers_no_hook(self):
		queue_outcome([])
		queue_outcome([None])
		self.assertNotIn(OUTCOME_FLAG, frappe.flags)


class TestItIsWiredIn(FrappeTestCase):
	def test_both_decided_states_are_covered(self):
		"""Approve transitions to Active rather than to an "Approved" state of its own."""
		self.assertEqual(set(DECIDED_STATES), {ACTIVE, REJECTED})

	def test_the_decision_queues_the_outcome(self):
		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "operations", "doctype", "employee_schedule", "employee_schedule.py"
			)
		)
		self.assertIn("dsot_notification.queue_outcome([self.name])", source)

	def test_the_expiry_job_goes_through_the_same_path(self):
		"""reject_expired_dsot_requests saves the document, so it reaches
		handle_dsot_decision and needs no wiring of its own."""
		source = frappe.read_file(
			frappe.get_app_path(
				"one_fm", "operations", "doctype", "employee_schedule", "employee_schedule.py"
			)
		)
		expiry = source.split("def reject_expired_dsot_requests()", 1)[1]
		self.assertIn("schedule.save(ignore_permissions=True)", expiry)
