# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002283: a second overtime shift waits for someone to say yes.

An employee already working a basic shift that day cannot simply be scheduled for
overtime on top of it. The request is held, blocks the Shift Assignment while it waits,
and is closed automatically if nobody answers before the shift has ended.
"""

import json

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_to_date, now_datetime, today

from one_fm.operations.doctype.employee_schedule.employee_schedule import (
	ACTIVE,
	BASIC,
	DSOT_REJECTED,
	OVERTIME,
	PENDING_DSOT,
	WORKING,
	hold_overtime_for_approval,
	may_decide_dsot,
	reject_expired_dsot_requests,
)

WORKFLOW_FILE = ("one_fm", "custom", "workflow", "employee_schedule.json")


def _workflow():
	return json.loads(frappe.read_file(frappe.get_app_path(*WORKFLOW_FILE)))


class TestTheValuesTheRuleTurnsOn(FrappeTestCase):
	"""The story writes "Overtime"; a rule keyed on the wrong spelling never fires."""

	def test_the_roster_type_is_the_one_the_field_offers(self):
		options = frappe.get_meta("Employee Schedule").get_field("roster_type").options.split("\n")

		self.assertIn(OVERTIME, options)
		self.assertIn(BASIC, options)
		self.assertNotIn("Overtime", options)

	def test_working_is_an_availability_the_field_offers(self):
		options = frappe.get_meta("Employee Schedule").get_field(
			"employee_availability").options.split("\n")

		self.assertIn(WORKING, options)


class TestTheWorkflow(FrappeTestCase):
	def setUp(self):
		self.workflow = _workflow()

	def test_the_pending_state_exists(self):
		self.assertIn(PENDING_DSOT, {s["state"] for s in self.workflow["states"]})

	def test_approving_lands_on_active(self):
		"""Not on a state of its own: only an Active schedule is picked up for a Shift
		Assignment, and only an Active one can later be suspended."""
		approvals = {
			t["next_state"] for t in self.workflow["transitions"]
			if t["state"] == PENDING_DSOT and t["action"] == "Approve"
		}

		self.assertEqual(approvals, {ACTIVE})

	def test_rejecting_lands_on_rejected(self):
		rejections = {
			t["next_state"] for t in self.workflow["transitions"]
			if t["state"] == PENDING_DSOT and t["action"] == "Reject"
		}

		self.assertEqual(rejections, {DSOT_REJECTED})

	def test_the_suspension_flow_is_untouched(self):
		"""It shares this workflow - Frappe runs one per doctype."""
		suspension = {
			(t["state"], t["action"], t["next_state"]) for t in self.workflow["transitions"]
		}

		self.assertIn(("Active", "Request Suspension", "Pending Suspension"), suspension)
		self.assertIn(("Pending Suspension", "Approve", "Suspended"), suspension)

	def test_an_approved_overtime_schedule_can_still_be_suspended(self):
		"""Because Approve lands on Active, it inherits the suspension route."""
		from_active = {
			t["action"] for t in self.workflow["transitions"] if t["state"] == ACTIVE
		}

		self.assertIn("Request Suspension", from_active)

	def test_every_state_carries_a_style(self):
		"""Workflow State.style is mandatory here; a state without one is never created
		and create_workflow logs the failure instead of raising."""
		for s in self.workflow["states"]:
			with self.subTest(state=s["state"]):
				self.assertTrue(s.get("style"))


class TestWhoMayDecide(FrappeTestCase):
	"""The workflow gates by role; the criteria name people."""

	def _settings(self, approver=None, manager=None):
		frappe.db.set_value("Operation Settings", "Operation Settings", {
			"dsot_approver": approver,
			"default_operation_manager": manager,
		})

	def tearDown(self):
		frappe.db.rollback()

	def _ordinary_user(self):
		"""Somebody with no System Manager role, so the check is actually exercised -
		Administrator would pass every one of these for the wrong reason."""
		for row in frappe.get_all(
			"User",
			filters={"enabled": 1, "name": ["not in", ["Administrator", "Guest"]]},
			pluck="name",
			limit=25,
		):
			if "System Manager" not in frappe.get_roles(row):
				return row
		self.skipTest("no enabled non-System-Manager user on this site")

	def test_the_named_approver_may(self):
		user = self._ordinary_user()
		self._settings(approver=user)

		self.assertTrue(may_decide_dsot(user))

	def test_the_named_operation_manager_may(self):
		"""AC: with no approver configured, the Operation Manager still decides."""
		user = self._ordinary_user()
		self._settings(approver=None, manager=user)

		self.assertTrue(may_decide_dsot(user))

	def test_somebody_named_nowhere_may_not(self):
		user = self._ordinary_user()
		self._settings(approver=None, manager=None)

		self.assertFalse(may_decide_dsot(user))

	def test_naming_somebody_else_does_not_let_them_in(self):
		user = self._ordinary_user()
		self._settings(approver="Administrator", manager="Administrator")

		self.assertFalse(may_decide_dsot(user))

	def test_a_system_manager_always_may(self):
		self._settings(approver=None, manager=None)

		self.assertTrue(may_decide_dsot("Administrator"))


class TestTheShiftAssignmentIsBlocked(FrappeTestCase):
	"""AC1: no Shift Assignment while the request waits, and none for a rejected one."""

	def test_the_nightly_job_skips_pending_and_rejected(self):
		source = frappe.read_file(frappe.get_app_path("one_fm", "api", "tasks.py"))

		self.assertIn('"workflow_state": ["not in", ["Pending DSOT Approval", "Rejected"]]', source)


class TestTheExpiryJob(FrappeTestCase):
	"""AC7: a request that outlives its own shift is closed - the hours are gone."""

	def test_it_reads_the_schedules_own_end_datetime(self):
		"""end_datetime already rolls onto the next day for an overnight shift, which is
		exactly the threshold the criteria describe."""
		source = frappe.read_file(frappe.get_app_path(
			"one_fm", "operations", "doctype", "employee_schedule", "employee_schedule.py"))

		self.assertIn("if start_time > end_time:", source)
		self.assertIn('"end_datetime": ["<", frappe.utils.now_datetime()]', source)

	def test_it_leaves_a_request_whose_shift_is_still_running(self):
		"""Nothing pending with a future end time should be touched."""
		pending = frappe.get_all(
			"Employee Schedule",
			filters={
				"workflow_state": PENDING_DSOT,
				"end_datetime": [">", now_datetime()],
			},
			pluck="name",
		)

		reject_expired_dsot_requests()

		for name in pending:
			with self.subTest(name=name):
				self.assertEqual(
					frappe.db.get_value("Employee Schedule", name, "workflow_state"), PENDING_DSOT
				)

	def test_it_returns_how_many_it_closed(self):
		self.assertIsInstance(reject_expired_dsot_requests(), int)

	def test_it_is_scheduled(self):
		hooks = frappe.read_file(frappe.get_app_path("one_fm", "hooks.py"))

		self.assertIn(
			"one_fm.operations.doctype.employee_schedule.employee_schedule."
			"reject_expired_dsot_requests",
			hooks,
		)


class TestTheApproverSetting(FrappeTestCase):
	def test_operation_settings_names_a_dsot_approver(self):
		field = frappe.get_meta("Operation Settings").get_field("dsot_approver")

		self.assertIsNotNone(field, "Operation Settings has no DSOT Approver field")
		self.assertEqual(field.options, "User")

	def test_it_still_names_an_operation_manager(self):
		"""The fallback the criteria rely on when no approver is set."""
		self.assertIsNotNone(
			frappe.get_meta("Operation Settings").get_field("default_operation_manager")
		)


class TestTheRosterPath(FrappeTestCase):
	"""The roster does not create schedules through the ORM.

	`assign_schedule` writes them with one raw INSERT - deliberately, it can be hundreds
	of rows at a time - so before_insert never runs and set_dsot_state never sees them.
	Rows arrived with no workflow_state at all and went straight through to a Shift
	Assignment, which is the whole thing this story exists to stop. Nothing else notices:
	the controller's own tests all create documents the ORM way and pass.
	"""

	def setUp(self):
		self.employee = frappe.db.get_value("Employee", {"status": "Active"}, "name")
		if not self.employee:
			self.skipTest("no active employee on this site")
		self.date = add_days(today(), 45)
		self.made = []

	def tearDown(self):
		for name in self.made:
			frappe.db.sql("DELETE FROM `tabEmployee Schedule` WHERE name = %s", name)

	def _raw_insert(self, roster_type):
		"""Exactly how the roster writes one: raw SQL, no workflow_state column."""
		name = f"{self.date}_{self.employee}_{roster_type}"
		frappe.db.sql(
			"""INSERT INTO `tabEmployee Schedule`
			   (`name`, `employee`, `date`, `roster_type`, `employee_availability`,
			    `owner`, `modified_by`, `creation`, `modified`)
			   VALUES (%s, %s, %s, %s, 'Working', 'Administrator', 'Administrator',
			           NOW(), NOW())""",
			(name, self.employee, self.date, roster_type),
		)
		self.made.append(name)
		return name

	def _state(self, name):
		return frappe.db.get_value("Employee Schedule", name, "workflow_state")

	def test_a_bulk_written_second_shift_is_held(self):
		self._raw_insert(BASIC)
		overtime = self._raw_insert(OVERTIME)
		self.assertIsNone(self._state(overtime), "the INSERT should not set a state itself")

		hold_overtime_for_approval([overtime])

		self.assertEqual(self._state(overtime), PENDING_DSOT)

	def test_overtime_on_a_day_off_is_not_held(self):
		"""Overtime on a day the employee is not already working is ordinary overtime."""
		overtime = self._raw_insert(OVERTIME)

		self.assertEqual(hold_overtime_for_approval([overtime]), [])
		self.assertIsNone(self._state(overtime))

	def test_a_decided_request_is_not_dragged_back(self):
		"""Re-running the roster over the same day must not undo an approval."""
		self._raw_insert(BASIC)
		overtime = self._raw_insert(OVERTIME)
		frappe.db.set_value("Employee Schedule", overtime, "workflow_state", ACTIVE)

		self.assertEqual(hold_overtime_for_approval([overtime]), [])
		self.assertEqual(self._state(overtime), ACTIVE)

	def test_running_it_twice_changes_nothing(self):
		self._raw_insert(BASIC)
		overtime = self._raw_insert(OVERTIME)

		self.assertEqual(hold_overtime_for_approval([overtime]), [overtime])
		self.assertEqual(hold_overtime_for_approval([overtime]), [])
		self.assertEqual(self._state(overtime), PENDING_DSOT)

	def test_it_asks_the_database_nothing_for_an_empty_batch(self):
		self.assertEqual(hold_overtime_for_approval([]), [])
		self.assertEqual(hold_overtime_for_approval(None), [])

	def test_the_roster_calls_it(self):
		"""A helper nothing calls fixes nothing - and the call sits inside the bulk
		insert branch, which no test exercises end to end."""
		source = frappe.read_file(
			frappe.get_app_path("one_fm", "one_fm", "page", "roster", "roster.py")
		)

		self.assertIn("hold_overtime_for_approval(inserted_names)", source)
