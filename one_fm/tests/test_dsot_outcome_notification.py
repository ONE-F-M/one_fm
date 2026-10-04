# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""What the requestor is told once their DSOT request has been decided."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, formatdate, today

from one_fm.operations.doctype.employee_schedule import dsot_notification
from one_fm.operations.doctype.employee_schedule.dsot_notification import (
	ACTIVE,
	DECIDED_STATES,
	OUTCOME_FLAG,
	PENDING_DSOT,
	REJECTED,
	SYSTEM_PROCESSOR,
	flush_outcomes,
	format_cycles,
	processed_by,
	queue_outcome,
	schedule_list_url,
)
from one_fm.operations.doctype.employee_schedule.employee_schedule import (
	BASIC,
	OVERTIME,
	hold_overtime_for_approval,
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


class TestOneEmailPerRequest(FrappeTestCase):
	"""Approvers decide one row per commit, so the email waits for the request's last row.

	Rows are written with raw SQL, as the roster writes them.
	"""

	def setUp(self):
		self.employees = frappe.get_all(
			"Employee", filters={"status": "Active"}, pluck="name", limit=2
		)
		if len(self.employees) < 2:
			self.skipTest("needs two active employees")
		self.sent = []
		mock = patch.object(
			dsot_notification,
			"send_outcome_email",
			side_effect=lambda **kwargs: self.sent.append(kwargs),
		)
		mock.start()
		self.addCleanup(mock.stop)

	def _row(self, employee, day, roster_type=OVERTIME, state=None, request=None):
		name = f"dsot-outcome-test-{frappe.generate_hash(length=8)}"
		frappe.db.sql(
			"""INSERT INTO `tabEmployee Schedule`
			   (`name`, `employee`, `date`, `roster_type`, `employee_availability`,
			    `workflow_state`, `dsot_request`, `owner`, `modified_by`, `creation`, `modified`)
			   VALUES (%s, %s, %s, %s, 'Working', %s, %s, 'Administrator', 'Administrator',
			           NOW(), NOW())""",
			(name, employee, add_days(today(), day), roster_type, state, request),
		)
		return name

	def _decide(self, names, state=ACTIVE):
		for name in names:
			frappe.db.set_value("Employee Schedule", name, "workflow_state", state)
			queue_outcome([name])
			flush_outcomes()

	def test_nothing_is_sent_while_part_of_the_request_is_pending(self):
		rows = [self._row(self.employees[0], d, state=PENDING_DSOT, request="req-a") for d in (10, 11, 12)]

		self._decide(rows[:2])

		self.assertEqual(self.sent, [])

	def test_deciding_row_by_row_sends_one_email_for_the_whole_request(self):
		"""AC3 through the form or the list view: each decision is its own commit."""
		rows = [self._row(self.employees[0], d, state=PENDING_DSOT, request="req-b") for d in (10, 11, 12)]

		self._decide([rows[0], rows[2]], ACTIVE)
		self._decide([rows[1]], REJECTED)

		self.assertEqual(len(self.sent), 1)
		decided = self.sent[0]["decided"]
		self.assertEqual({r.name for r in decided}, set(rows))
		self.assertEqual([r.name for r in decided if r.workflow_state == REJECTED], [rows[1]])

	def test_two_requests_decided_together_are_two_emails(self):
		first = self._row(self.employees[0], 10, state=PENDING_DSOT, request="req-c")
		second = self._row(self.employees[1], 10, state=PENDING_DSOT, request="req-d")

		for name in (first, second):
			frappe.db.set_value("Employee Schedule", name, "workflow_state", ACTIVE)
		queue_outcome([first, second])
		flush_outcomes()

		self.assertEqual(len(self.sent), 2)

	def test_a_row_held_before_requests_existed_is_a_request_of_one(self):
		legacy = self._row(self.employees[0], 10, state=PENDING_DSOT)

		self._decide([legacy])

		self.assertEqual([r.name for r in self.sent[0]["decided"]], [legacy])

	def test_a_roster_run_holds_one_request_per_employee(self):
		names = []
		for employee in self.employees:
			for day in (20, 21):
				self._row(employee, day, roster_type=BASIC, state=ACTIVE)
				names.append(self._row(employee, day))

		hold_overtime_for_approval(names)

		rows = frappe.get_all(
			"Employee Schedule",
			filters={"name": ["in", names]},
			fields=["employee", "workflow_state", "dsot_request"],
		)
		self.assertTrue(all(r.workflow_state == PENDING_DSOT and r.dsot_request for r in rows))
		by_employee = {}
		for r in rows:
			by_employee.setdefault(r.employee, set()).add(r.dsot_request)
		self.assertTrue(all(len(requests) == 1 for requests in by_employee.values()))
		self.assertEqual(len(set.union(*by_employee.values())), 2)

	def test_a_re_requested_rejected_day_joins_the_new_request(self):
		"""The roster reuses a rejected row's name, so the old request must not keep it."""
		employee = self.employees[0]
		self._row(employee, 30, roster_type=BASIC, state=ACTIVE)
		rejected = self._row(employee, 30, state=REJECTED, request="req-old")

		hold_overtime_for_approval([rejected])

		self.assertNotEqual(
			frappe.db.get_value("Employee Schedule", rejected, "dsot_request"), "req-old"
		)
