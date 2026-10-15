# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002602: one DSOT approval email per employee per continuous date cycle.

Every Employee Schedule entering ``Pending DSOT Approval`` put its own assignment in front
of the DSOT Approver as a normal assignment, so ERPNext sent one Assignment Notification
per row. A week of overtime for one person is eight rows and was eight near-identical emails,
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
		# AC4. The grouping key is the employee, so the same day for two people is two
		# emails rather than one. Pinned on the code that does it.
		source = inspect.getsource(dsot_notification.flush)
		self.assertIn("by_employee.setdefault((row.employee, row.employee_name), [])", source)
		self.assertIn("send_urgent_email(approver, employee, employee_name or employee", source)


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
		# ``assign_to.add`` has no "notify" argument - it ignores one entirely and always
		# calls notify_assignment. Naming the approver as the assigner is what silences
		# the mail, and the behaviour that makes it work is pinned below.
		source = inspect.getsource(employee_schedule.EmployeeSchedule.request_dsot_approval)
		self.assertIn('"assigned_by": approver,', source)
		self.assertNotIn('"notify":', source)

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
		# serves every assignment in the system, so this flow renders one_fm's existing
		# notification table itself instead of editing what everything else uses.
		source = inspect.getsource(dsot_notification.send_cycle_email)
		self.assertIn("one_fm/templates/emails/notification_log.html", source)

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


class TestThePerRowMailIsActuallyGone(FrappeTestCase):
	"""The Frappe behaviour the suppression rests on, exercised rather than assumed."""

	def test_frappe_skips_the_notification_when_the_assigner_is_the_assignee(self):
		# This is the whole mechanism: ``assign_to.add`` ignores a "notify" argument and
		# always calls notify_assignment, which returns without notifying a user who
		# assigned the task to themselves. If a future Frappe drops that early return,
		# the flood comes back silently - so it is asserted here rather than trusted.
		from frappe.desk.form import assign_to

		# An existing enabled user rather than a new one: User.insert commits on its way
		# through, so a created account would outlive the rollback and collide on the
		# next run.
		user = frappe.db.get_value(
			"User", {"enabled": 1, "name": ["not in", ("Administrator", "Guest")]}, "name"
		)
		reference = frappe.get_all("Employee Schedule", pluck="name", limit=1)
		if not (user and reference):
			self.skipTest("no enabled user / Employee Schedule on this site to assign")

		notified = []
		original = assign_to.enqueue_create_notification
		assign_to.enqueue_create_notification = lambda users, doc: notified.append(users)
		try:
			# Control: a normal assignment still notifies, so a green test below means the
			# suppression worked and not that the call did nothing either way.
			assign_to.notify_assignment(
				"Administrator", user, "Employee Schedule", reference[0], action="ASSIGN"
			)
			assign_to.notify_assignment(
				user, user, "Employee Schedule", reference[0], action="ASSIGN"
			)
		finally:
			assign_to.enqueue_create_notification = original

		self.assertEqual(notified, [user])


class TestTheBodyReadsLikeAnAssignment(FrappeTestCase):
	"""AC5's body: the same table every other assignment email on this site arrives in."""

	def body(self, start_day=13, end_day=20, shifts=8):
		from frappe.utils import getdate

		sent = {}
		original = dsot_notification.sendemail
		dsot_notification.sendemail = lambda **kwargs: sent.update(kwargs)
		try:
			dsot_notification.send_cycle_email(
				approver="Administrator",
				employee="HR-EMP-00001",
				employee_name="Test Employee",
				start=getdate(SEPT % start_day),
				end=getdate(SEPT % end_day),
				shifts=[frappe._dict(name="ES-TEST")] * shifts,
			)
		finally:
			dsot_notification.sendemail = original
		return sent.get("content") or ""

	def test_it_is_the_same_table_the_other_assignment_emails_use(self):
		# The five rows of one_fm/templates/emails/notification_log.html, which is what
		# every Notification Log email on this site is rendered through.
		body = self.body()
		for label in ("Document Name", "Document Type", "Description", "Content", "Document Link"):
			self.assertIn(f"<th>{label}</th>", body)

	def test_the_cycle_is_what_the_approver_is_told_to_act_on(self):
		# The single-row assignment named one date; this one has to name the range and
		# its size, or the approver cannot tell what they are being asked to clear.
		body = self.body()
		self.assertIn("13-09-2026 to 20-09-2026 (Total: 8 Shifts)", body)
		self.assertIn("Test Employee", body)

	def test_the_link_opens_the_pending_cycle_not_one_schedule(self):
		# AC6: the approver has to act on the whole cycle, and Bulk Approve lives in the
		# List View.
		body = self.body()
		self.assertIn("/app/employee-schedule?", body)
		self.assertNotIn("/app/employee-schedule/ES-TEST", body)

	def test_a_one_day_request_does_not_read_as_a_range(self):
		body = self.body(start_day=13, end_day=13, shifts=1)
		self.assertIn("on 13-09-2026", body)
		self.assertNotIn("from 13-09-2026", body)
		self.assertNotIn("Total:", body)


def schedule_row(name, employee="HR-EMP-00001", date=None, **extra):
	return frappe._dict(
		name=name,
		employee=employee,
		employee_name=extra.pop("employee_name", "Test Employee"),
		date=date or frappe.utils.today(),
		shift=extra.pop("shift", "Test Shift"),
		shift_type=extra.pop("shift_type", "Day"),
		**extra,
	)


class TestImmediateEmailIsSameDayOnly(FrappeTestCase):
	"""flush() mails today's rows at once, per employee, and leaves the rest to the digest."""

	def flush(self, rows, approver="approver@example.com"):
		from unittest import mock

		sent = []
		frappe.flags[dsot_notification.FLAG] = {row.name for row in rows}
		with mock.patch.object(
			frappe.db, "get_single_value", return_value=approver
		), mock.patch.object(frappe, "get_all", return_value=rows), mock.patch.object(
			dsot_notification, "send_urgent_email", side_effect=lambda *args: sent.append(args)
		):
			dsot_notification.flush()
		frappe.flags.pop(dsot_notification.FLAG, None)
		return sent

	def test_a_future_dated_row_is_not_emailed(self):
		future = frappe.utils.add_days(frappe.utils.today(), 3)
		self.assertEqual(self.flush([schedule_row("ES-1", date=future)]), [])

	def test_a_past_dated_row_is_not_emailed(self):
		past = frappe.utils.add_days(frappe.utils.today(), -1)
		self.assertEqual(self.flush([schedule_row("ES-1", date=past)]), [])

	def test_only_todays_rows_are_emailed_when_dates_are_mixed(self):
		future = frappe.utils.add_days(frappe.utils.today(), 3)
		sent = self.flush([schedule_row("ES-1"), schedule_row("ES-2", date=future)])
		self.assertEqual(len(sent), 1)
		self.assertEqual([row.name for row in sent[0][3]], ["ES-1"])

	def test_rows_are_grouped_per_employee(self):
		rows = [
			schedule_row("ES-1", employee="HR-EMP-00001"),
			schedule_row("ES-2", employee="HR-EMP-00002", employee_name="Other"),
			schedule_row("ES-3", employee="HR-EMP-00001"),
		]
		sent = self.flush(rows)
		self.assertEqual(len(sent), 2)
		self.assertEqual(sorted(len(args[3]) for args in sent), [1, 2])

	def test_the_subject_says_urgent(self):
		source = inspect.getsource(dsot_notification.send_urgent_email)
		self.assertIn('_("Urgent DSOT Approval Request: {0} ({1})")', source)

	def test_the_assignment_and_the_commit_hook_are_unchanged(self):
		source = inspect.getsource(dsot_notification.queue)
		self.assertIn("frappe.db.after_commit.add(flush)", source)
		self.assertIn('"assigned_by": approver,', inspect.getsource(
			employee_schedule.EmployeeSchedule.request_dsot_approval
		))


class TestTheSharedTemplate(FrappeTestCase):
	def render(self, rows=None):
		rows = rows if rows is not None else [schedule_row("ES-1")]
		return dsot_notification.render_approval_request(
			"approver@example.com", rows, "Intro", digest_cutoff="2026-09-13 00:05:00"
		)

	def test_the_header_has_both_bulk_buttons_and_the_columns(self):
		html = self.render()
		for text in (
			"Approve All", "Reject All", "Date", "Employee ID", "Employee Name",
			"Basic (Shift Name)", "DSOT (Shift Name)", "Action",
		):
			self.assertIn(text, html)

	def test_each_row_has_its_own_approve_and_reject_links(self):
		html = self.render([schedule_row("ES-1"), schedule_row("ES-2")])
		self.assertEqual(html.count(">Approve</a>"), 2)
		self.assertEqual(html.count(">Reject</a>"), 2)
		self.assertIn("confirm_email_action", html)
		self.assertIn("_signature=", html)

	def test_the_bulk_links_sign_a_cutoff_not_a_name_list(self):
		html = self.render([schedule_row("ES-1"), schedule_row("ES-2")])
		self.assertIn("digest_cutoff=", html)
		# The only names in the email are the per-row ones.
		self.assertNotIn("names=ES-1%2CES-2", html)

	def test_styles_are_inline(self):
		html = self.render()
		self.assertIn('style="', html)
		self.assertNotIn("<style", html)


class TestTheDailyDigest(FrappeTestCase):
	def run_digest(self, approver="approver@example.com", rows=None):
		from unittest import mock

		with mock.patch.object(
			frappe.db, "get_single_value", return_value=approver
		), mock.patch.object(
			dsot_notification, "pending_overtime_rows", return_value=rows or []
		), mock.patch.object(dsot_notification, "sendemail") as send:
			dsot_notification.send_daily_dsot_digest()
		return send

	def test_nothing_is_sent_without_an_approver(self):
		self.run_digest(approver=None, rows=[schedule_row("ES-1")]).assert_not_called()

	def test_nothing_is_sent_when_there_are_no_rows(self):
		self.run_digest(rows=[]).assert_not_called()

	def test_one_email_carries_every_row(self):
		rows = [schedule_row(f"ES-{i}") for i in range(5)]
		send = self.run_digest(rows=rows)
		send.assert_called_once()
		kwargs = send.call_args.kwargs
		self.assertEqual(kwargs["subject"], "DSOT Approval Request: 5 Pending Overtime Requests")
		self.assertTrue(kwargs["is_scheduler_email"])
		self.assertEqual(kwargs["content"].count(">Approve</a>"), 5)

	def test_a_failed_send_is_logged_not_raised(self):
		from unittest import mock

		with mock.patch.object(
			frappe.db, "get_single_value", return_value="approver@example.com"
		), mock.patch.object(
			dsot_notification, "pending_overtime_rows", return_value=[schedule_row("ES-1")]
		), mock.patch.object(
			dsot_notification, "sendemail", side_effect=Exception("smtp down")
		), mock.patch.object(frappe, "log_error") as log_error:
			dsot_notification.send_daily_dsot_digest()
		log_error.assert_called_once()

	def test_the_query_rules(self):
		source = inspect.getsource(dsot_notification.pending_overtime_rows)
		self.assertIn("frappe.qb", source)
		self.assertIn("OVERTIME", source)
		self.assertIn("fn.Date(schedule.creation) != schedule.date", source)
		self.assertIn("orderby(schedule.employee).orderby(schedule.date)", source)

	def test_it_is_scheduled_once_at_five_past_midnight(self):
		from one_fm import hooks

		self.assertEqual(
			hooks.scheduler_events["cron"]["5 0 * * *"],
			["one_fm.operations.doctype.employee_schedule.dsot_notification.send_daily_dsot_digest"],
		)


class TestTheEmailActionEndpoints(FrappeTestCase):
	def test_both_are_guest_get_endpoints(self):
		for function in (dsot_notification.apply_email_action, dsot_notification.confirm_email_action):
			self.assertIn(function, frappe.whitelisted)
			self.assertIn(function, frappe.guest_methods)
			self.assertEqual(frappe.allowed_http_methods_for_whitelisted_func[function], ["GET"])

	def test_a_bad_signature_does_nothing(self):
		from unittest import mock

		with mock.patch.object(dsot_notification, "verify_request", return_value=False), mock.patch(
			"one_fm.overrides.workflow.apply_workflow"
		) as apply, mock.patch.object(frappe.db, "commit") as commit:
			dsot_notification.apply_email_action(action="Approve", user="Administrator", names="ES-1")
		apply.assert_not_called()
		commit.assert_not_called()

	def test_only_approve_or_reject_is_accepted(self):
		from unittest import mock

		with mock.patch.object(dsot_notification, "verify_request", return_value=True), mock.patch(
			"one_fm.overrides.workflow.apply_workflow"
		) as apply:
			dsot_notification.apply_email_action(action="Delete", user="Administrator", names="ES-1")
		apply.assert_not_called()

	def test_the_user_is_restored_and_nothing_is_committed_for_a_stranger(self):
		from unittest import mock

		before = frappe.session.user
		with mock.patch.object(dsot_notification, "verify_request", return_value=True), mock.patch(
			"one_fm.operations.doctype.employee_schedule.employee_schedule.may_decide_dsot",
			return_value=False,
		), mock.patch("one_fm.overrides.workflow.apply_workflow") as apply, mock.patch.object(
			frappe.db, "commit"
		) as commit:
			dsot_notification.apply_email_action(action="Approve", user="Administrator", names="ES-1")
		self.assertEqual(frappe.session.user, before)
		apply.assert_not_called()
		commit.assert_not_called()

	def test_it_commits_once_and_skips_rows_already_decided(self):
		from unittest import mock

		states = {"ES-1": dsot_notification.PENDING_DSOT, "ES-2": "Active", "ES-3": None}
		with mock.patch.object(dsot_notification, "verify_request", return_value=True), mock.patch(
			"one_fm.operations.doctype.employee_schedule.employee_schedule.may_decide_dsot",
			return_value=True,
		), mock.patch(
			"one_fm.overrides.workflow.apply_workflow", return_value=frappe._dict()
		) as apply, mock.patch.object(
			frappe.db, "get_value", side_effect=lambda dt, name, field: states[name]
		), mock.patch.object(frappe, "get_doc"), mock.patch.object(
			frappe.db, "savepoint"
		), mock.patch.object(frappe.db, "commit") as commit, mock.patch.object(
			dsot_notification, "respond_email_action_page"
		) as page:
			dsot_notification.apply_email_action(
				action="Approve", user="Administrator", names="ES-1,ES-2,ES-3"
			)
		self.assertEqual(apply.call_count, 1)
		commit.assert_called_once()
		html = page.call_args.args[1]
		self.assertIn("Approved: 1", html)
		self.assertIn("Rejected: 0", html)
		self.assertIn("Skipped: 2", html)

	def test_a_failing_row_is_rolled_back_logged_and_skipped(self):
		from unittest import mock

		with mock.patch.object(dsot_notification, "verify_request", return_value=True), mock.patch(
			"one_fm.operations.doctype.employee_schedule.employee_schedule.may_decide_dsot",
			return_value=True,
		), mock.patch(
			"one_fm.overrides.workflow.apply_workflow", side_effect=Exception("boom")
		), mock.patch.object(
			frappe.db, "get_value", return_value=dsot_notification.PENDING_DSOT
		), mock.patch.object(frappe, "get_doc"), mock.patch.object(
			frappe.db, "savepoint"
		), mock.patch.object(frappe.db, "rollback") as rollback, mock.patch.object(
			frappe, "log_error"
		) as log_error, mock.patch.object(frappe.db, "commit"), mock.patch.object(
			dsot_notification, "respond_email_action_page"
		) as page:
			dsot_notification.apply_email_action(action="Reject", user="Administrator", names="ES-1")
		rollback.assert_called_once_with(save_point=dsot_notification.SAVEPOINT)
		log_error.assert_called_once()
		self.assertIn("Skipped: 1", page.call_args.args[1])

	def test_the_confirm_page_changes_nothing_and_links_to_the_signed_apply_url(self):
		from unittest import mock

		row = frappe._dict(
			name="ES-1", employee="HR-EMP-00001", employee_name="Test Employee",
			date=frappe.utils.today(), workflow_state=dsot_notification.PENDING_DSOT,
		)
		with mock.patch.object(dsot_notification, "verify_request", return_value=True), mock.patch.object(
			frappe.db, "get_value", return_value=row
		), mock.patch.object(frappe.db, "commit") as commit, mock.patch(
			"one_fm.overrides.workflow.apply_workflow"
		) as apply, mock.patch.object(dsot_notification, "respond_email_action_page") as page:
			dsot_notification.confirm_email_action(action="Approve", user="Administrator", names="ES-1")
		commit.assert_not_called()
		apply.assert_not_called()
		self.assertIn("apply_email_action", page.call_args.kwargs["primary_action"])
		self.assertIn("_signature=", page.call_args.kwargs["primary_action"])
		self.assertEqual(page.call_args.kwargs["primary_label"], "Confirm")

	def test_bulk_selection_uses_the_cutoff_rule(self):
		source = inspect.getsource(dsot_notification.selected_schedules)
		self.assertIn("pending_overtime_rows(digest_cutoff)", source)
		self.assertIn("creation <= cutoff", inspect.getsource(dsot_notification.pending_overtime_rows))

	def test_the_workflow_is_not_set_to_send_its_own_email(self):
		# Approve stays the existing Active transition and no Notification is added.
		self.assertNotIn("send_email_alert", inspect.getsource(dsot_notification))
