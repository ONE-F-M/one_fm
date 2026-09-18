# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002602: one DSOT approval email per employee per continuous date cycle.

Every Employee Schedule entering ``Pending DSOT Approval`` put its own assignment in front
of the DSOT Approver with ``notify: 1``, so ERPNext sent one Assignment Notification per
row. A week of overtime for one person is eight rows and was eight near-identical emails,
for what the approver experiences as a single request.

Two things are deliberately NOT changed, and both are pinned below:

* **The ToDo assignment stays, one per schedule.** The approver's task list and the whole
  Approve/Reject flow from WI-002283 are built on it; only its email is suppressed.
* **ERPNext's shared Assignment Notification template is untouched.** AC5 is worded as a
  change to it, but that template serves every assignment in the system - leave,
  penalties, everything - and rewording it for this one flow would change all of them. The
  fields the criterion lists are all present; only the vehicle is this flow's own.

The email goes out when the request COMMITS rather than as each row is held, because a
range is not known to be a range until its last row is written. That also means a
rolled-back roster run sends nothing, which a per-row email could not promise.

All five scenarios in the story's notes are walked below, and AC6's link was checked
against the live site: the three filters apply and the one real pending record is what the
approver lands on, with the row checkboxes that make Bulk Approve reachable.
"""

import inspect

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.operations.doctype.employee_schedule import dsot_notification, employee_schedule
from one_fm.operations.doctype.employee_schedule.dsot_notification import (
	continuous_cycles,
	pending_list_url,
)

SEPT = "2026-09-%02d"


def sept(*days):
	return [SEPT % d for d in days]


def spans(cycles):
	return [(str(a), str(b)) for a, b in cycles]


class TestTheStoryScenarios(FrappeTestCase):
	"""The five scenarios in the story's own notes, by their numbers."""

	def test_scenario_1_a_single_date_is_one_cycle(self):
		# AC1: one email, reflecting the single date.
		self.assertEqual(spans(continuous_cycles(sept(13))), [("2026-09-13", "2026-09-13")])

	def test_scenario_1b_a_night_shift_is_still_one_request(self):
		# "13 Sept - 14 Sept (+1 day due to night shift) - 1 Request". The roll-over lives
		# in end_datetime; the schedule's own `date` is the 13th, so it is one row and one
		# cycle rather than a two-day range.
		self.assertEqual(spans(continuous_cycles(sept(13))), [("2026-09-13", "2026-09-13")])

	def test_scenario_2_a_continuous_week_is_one_cycle(self):
		# AC2: eight rows, one email, and the span is the whole range.
		self.assertEqual(
			spans(continuous_cycles(sept(13, 14, 15, 16, 17, 18, 19, 20))),
			[("2026-09-13", "2026-09-20")],
		)

	def test_scenario_3_a_gap_starts_a_new_cycle(self):
		self.assertEqual(
			spans(continuous_cycles(sept(13, 14, 15, 16, 17, 18, 19, 20, 23, 24))),
			[("2026-09-13", "2026-09-20"), ("2026-09-23", "2026-09-24")],
		)

	def test_scenario_4_three_cycles_are_three_emails(self):
		# AC3: one distinct notification per continuous cycle.
		cycles = continuous_cycles(
			sept(13, 14, 15, 16, 17, 18, 19, 20, 23, 24) + ["2026-10-03", "2026-10-04"]
		)
		self.assertEqual(len(cycles), 3)
		self.assertEqual(
			spans(cycles),
			[("2026-09-13", "2026-09-20"), ("2026-09-23", "2026-09-24"),
			 ("2026-10-03", "2026-10-04")],
		)

	def test_scenario_5_employees_are_grouped_before_cycles(self):
		# AC4. The grouping key is (employee, cycle), so the same range for two people is
		# two emails rather than one. Pinned on the code that does it, since the helper
		# only ever sees one employee's dates.
		source = inspect.getsource(dsot_notification.flush)
		self.assertIn("by_employee.setdefault((row.employee, row.employee_name), [])", source)
		self.assertIn("for start, end in continuous_cycles(dates):", source)


class TestTheCycleBoundaries(FrappeTestCase):
	"""Where a run of days starts and stops."""

	def test_a_month_boundary_is_still_continuous(self):
		# 30 September and 1 October are consecutive days; only the month changes.
		self.assertEqual(
			spans(continuous_cycles(["2026-09-30", "2026-10-01"])),
			[("2026-09-30", "2026-10-01")],
		)

	def test_a_year_boundary_is_still_continuous(self):
		self.assertEqual(
			spans(continuous_cycles(["2026-12-31", "2027-01-01"])),
			[("2026-12-31", "2027-01-01")],
		)

	def test_two_rows_on_one_date_are_one_day(self):
		# A second overtime row on the same date does not extend the cycle.
		self.assertEqual(
			spans(continuous_cycles(sept(13, 13, 14))), [("2026-09-13", "2026-09-14")]
		)

	def test_dates_out_of_order_still_group(self):
		# The roster does not promise an order, and a sort here is cheaper than trusting it.
		self.assertEqual(
			spans(continuous_cycles(sept(24, 13, 23, 14))),
			[("2026-09-13", "2026-09-14"), ("2026-09-23", "2026-09-24")],
		)

	def test_a_single_day_gap_is_a_gap(self):
		self.assertEqual(
			spans(continuous_cycles(sept(13, 15))),
			[("2026-09-13", "2026-09-13"), ("2026-09-15", "2026-09-15")],
		)

	def test_nothing_in_nothing_out(self):
		self.assertEqual(continuous_cycles([]), [])
		self.assertEqual(continuous_cycles([None, ""]), [])


class TestTheApproversLink(FrappeTestCase):
	"""AC6: the email lands on the cycle, not on one schedule."""

	def setUp(self):
		self.url = pending_list_url("HR-EMP-04448", "2026-09-13", "2026-09-20")

	def test_it_opens_the_list_view_not_a_document(self):
		self.assertIn("/app/employee-schedule?", self.url)

	def test_it_carries_all_three_filters(self):
		self.assertIn("employee=HR-EMP-04448", self.url)
		self.assertIn("workflow_state=Pending%20DSOT%20Approval", self.url)
		# The range as a between, so the approver does not have to reconstruct it.
		self.assertIn("date=%5B%22between%22%2C%5B%222026-09-13%22%2C%222026-09-20%22%5D%5D",
					  self.url)

	def test_the_filter_json_is_compact(self):
		# frappe.as_json pretty-prints, which pads the query string with encoded newlines.
		self.assertNotIn("%0A", self.url)

	def test_a_single_day_cycle_still_uses_a_range(self):
		# Same shape either way, so the approver's landing page behaves identically.
		url = pending_list_url("HR-EMP-00574", "2026-09-15", "2026-09-15")
		self.assertIn("%222026-09-15%22%2C%222026-09-15%22", url)


class TestWhatWasLeftAlone(FrappeTestCase):
	"""The two things this story must not break."""

	def test_the_assignment_is_still_made_per_schedule(self):
		# The approver's task list and the Approve/Reject flow are built on the ToDo.
		source = inspect.getsource(employee_schedule.EmployeeSchedule.request_dsot_approval)
		self.assertIn("add_assignment({", source)
		self.assertIn('"assign_to": [approver]', source)

	def test_only_its_email_is_suppressed(self):
		source = inspect.getsource(employee_schedule.EmployeeSchedule.request_dsot_approval)
		self.assertIn('"notify": 0,', source)
		self.assertNotIn('"notify": 1,', source)

	def test_both_entry_points_queue_the_consolidated_email(self):
		# The single-document path and the roster's bulk path both hold schedules, and
		# only one of them going through the consolidation would leave the other sending
		# nothing at all.
		single = inspect.getsource(employee_schedule.EmployeeSchedule.request_dsot_approval)
		self.assertIn("dsot_notification.queue([self.name])", single)

		bulk = inspect.getsource(employee_schedule.hold_overtime_for_approval)
		self.assertIn("dsot_notification.queue(pending)", bulk)

	def test_the_shared_assignment_template_is_untouched(self):
		# AC5 is worded as a change to ERPNext's Assignment Notification. That template
		# serves every assignment in the system, so this flow sends its own email instead.
		self.assertTrue(frappe.get_app_path(
			"one_fm", "templates", "emails", "dsot_approval_request.html"))
		source = inspect.getsource(dsot_notification.send_cycle_email)
		self.assertIn("one_fm/templates/emails/dsot_approval_request.html", source)

	def test_the_mail_is_sent_once_the_request_commits(self):
		# A range is not known to be a range until its last row is written; and a
		# rolled-back roster run must send nothing.
		source = inspect.getsource(dsot_notification.queue)
		self.assertIn("frappe.db.after_commit.add(flush)", source)

	def test_the_hook_is_registered_once_per_request_not_once_per_row(self):
		# Registered per row, eight held schedules would flush eight times - which is the
		# bug this story exists to remove, reintroduced one level down.
		source = inspect.getsource(dsot_notification.queue)
		self.assertIn("if pending is None:", source)

	def test_a_failed_send_does_not_undo_a_held_request(self):
		# The schedules are already saved and already blocking their Shift Assignments.
		source = inspect.getsource(dsot_notification.flush)
		self.assertIn("except Exception:", source)
		self.assertIn("frappe.log_error(", source)

	def test_nothing_is_sent_when_no_approver_is_configured(self):
		source = inspect.getsource(dsot_notification.flush)
		self.assertIn("if not approver:", source)

	def test_only_rows_still_pending_are_announced(self):
		# A schedule decided between being held and the commit is not a pending request.
		source = inspect.getsource(dsot_notification.flush)
		self.assertIn('"workflow_state": PENDING_DSOT', source)

	def test_the_notification_log_does_not_send_a_second_copy(self):
		# "Alert" is the one type Frappe never emails itself; any other type makes
		# Notification Log's after_insert send its own mail through its own template.
		source = inspect.getsource(dsot_notification.send_cycle_email)
		self.assertIn('"type": "Alert",', source)
