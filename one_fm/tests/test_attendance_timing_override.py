# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-001835: Late Entry / Early Exit measured against the override day's own hours.

No production code changed for this story, and the tests are the deliverable. Everything
the attendance calculation reads - shift_actual_start, shift_actual_end and the grace
periods - comes off the Shift Assignment, which WI-001833 already made day-resolved. What
was missing was proof that the chain holds end to end, and a guard against a later change
quietly re-benchmarking an override day against the default hours again.

The arithmetic under test is one_fm.overrides.employee_checkin.after_insert_background:

    late_entry  <- (checkin_time - late_entry_grace_period)  > assignment.start_datetime
    early_exit  <- (checkin_time + early_exit_grace_period)  < assignment.end_datetime
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, get_datetime, getdate, today

from one_fm.overrides.employee_checkin import after_insert_background

# Dated relative to today, not pinned: a Shift Assignment cannot be created for a date
# later than today ("Shift cannot be created for date greater than today"), so the
# override is put on today's own day of the week and the unchanged-behaviour case uses
# yesterday, which is necessarily a different day of the week.


def _an_operations_shift():
	name = frappe.db.get_value(
		"Operations Shift",
		{"status": "Active", "shift_type": ["is", "set"]},
		"name",
		order_by="creation asc",
	)
	if not name:
		raise frappe.DoesNotExistError("No active Operations Shift on this site to test against")
	return name


def _an_active_employee():
	name = frappe.db.get_value(
		"Employee",
		{"status": "Active", "relieving_date": ["is", "not set"]},
		"name",
		order_by="creation asc",
	)
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return name


class TestAttendanceTimingOverride(FrappeTestCase):
	def setUp(self):
		self.override_date = today()
		self.override_day = getdate(self.override_date).strftime("%A")
		self.default_date = add_days(self.override_date, -1)

		self.employee = _an_active_employee()
		self.shift_name = _an_operations_shift()
		self.shift = frappe.get_doc("Operations Shift", self.shift_name)
		self.default_type = self.shift.shift_type

		# A later-starting Shift Type, so an arrival that is late against the default is
		# comfortably on time against the override. That contrast is the whole story.
		default_start = frappe.db.get_value("Shift Type", self.default_type, "start_time")
		self.override_type = frappe.db.get_value(
			"Shift Type",
			{"name": ["!=", self.default_type], "start_time": [">", default_start]},
			"name",
			order_by="start_time asc",
		)
		if not self.override_type:
			self.skipTest("No later-starting Shift Type on this site to override with")

		self._set_override(True)

	def tearDown(self):
		self._set_override(False)
		for date in (self.override_date, self.default_date):
			frappe.db.delete("Employee Checkin", {"employee": self.employee, "date": date})
			frappe.db.delete("Shift Assignment", {"employee": self.employee, "start_date": date})

	def _set_override(self, on):
		"""Configure the post with direct writes, so saving it does not enqueue the re-stamp."""
		frappe.db.set_value(
			"Operations Shift", self.shift_name, "shift_timing_override_required", int(on),
			update_modified=False,
		)
		frappe.db.delete(
			"Operations Shift Timing",
			{"parent": self.shift_name, "parenttype": "Operations Shift"},
		)
		if on:
			frappe.get_doc({
				"doctype": "Operations Shift Timing",
				"parent": self.shift_name,
				"parenttype": "Operations Shift",
				"parentfield": "operations_shift_timing",
				"idx": 1,
				"day_of_week": self.override_day,
				"shift_type": self.override_type,
			}).db_insert()
		frappe.clear_document_cache("Operations Shift", self.shift_name)

	def _assignment(self, date):
		"""A submitted Shift Assignment for one date, resolved by WI-001833.

		Any assignment the site already holds for that employee and date is cleared first,
		or the overlap check rejects this one before validate can resolve anything.
		"""
		frappe.db.delete("Shift Assignment", {"employee": self.employee, "start_date": date})
		assignment = frappe.get_doc({
			"doctype": "Shift Assignment",
			"employee": self.employee,
			"company": frappe.defaults.get_user_default("company"),
			"shift": self.shift_name,
			"shift_type": self.default_type,
			"start_date": date,
			"status": "Active",
			"roster_type": "Basic",
		})
		assignment.flags.ignore_permissions = True
		assignment.insert(ignore_permissions=True)
		assignment.submit()
		return assignment

	def _grace(self, shift_type):
		return frappe.db.get_value(
			"Shift Type",
			shift_type,
			["enable_entry_grace_period", "late_entry_grace_period", "early_exit_grace_period"],
			as_dict=True,
		)

	def _checkin(self, assignment, time, log_type="IN"):
		"""An Employee Checkin put through the real flagging path."""
		checkin = frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": self.employee,
			"log_type": log_type,
			"time": time,
			"shift_assignment": assignment.name,
			"skip_auto_attendance": 0,
		})
		checkin.flags.ignore_permissions = True
		checkin.flags.ignore_validate = True
		checkin.insert(ignore_permissions=True)

		after_insert_background(checkin.name, assignment.name)
		checkin.reload()
		return checkin

	# ------------------------------------------------- the benchmark is the override's

	def test_the_override_day_assignment_holds_the_override_hours(self):
		assignment = self._assignment(self.override_date)

		self.assertEqual(assignment.shift_type, self.override_type)
		override_start = frappe.db.get_value("Shift Type", self.override_type, "start_time")
		self.assertEqual(assignment.start_datetime, get_datetime(f"{self.override_date} {override_start}"))

	def test_the_checkin_is_stamped_with_the_override_hours(self):
		assignment = self._assignment(self.override_date)

		checkin = self._checkin(assignment, assignment.start_datetime)

		self.assertEqual(get_datetime(checkin.shift_actual_start), assignment.start_datetime)
		self.assertEqual(get_datetime(checkin.shift_actual_end), assignment.end_datetime)
		self.assertEqual(checkin.shift_type, self.override_type)

	def test_arriving_on_time_for_the_override_is_not_late(self):
		# The point of the story: this arrival is well past the default's start time, so
		# before the override existed it would have been flagged late on this day.
		assignment = self._assignment(self.override_date)
		default_start = get_datetime(
			f"{self.override_date} {frappe.db.get_value('Shift Type', self.default_type, 'start_time')}"
		)
		self.assertGreater(assignment.start_datetime, default_start)

		checkin = self._checkin(assignment, assignment.start_datetime)

		self.assertEqual(checkin.late_entry, 0)

	def test_arriving_late_for_the_override_is_late(self):
		assignment = self._assignment(self.override_date)
		grace = self._grace(self.override_type)
		if not grace.enable_entry_grace_period:
			self.skipTest(f"{self.override_type} has no entry grace period configured")
		late_by = frappe.utils.add_to_date(
			assignment.start_datetime, minutes=(grace.late_entry_grace_period or 0) + 5
		)

		checkin = self._checkin(assignment, late_by)

		self.assertEqual(checkin.late_entry, 1)

	def test_leaving_before_the_override_ends_is_an_early_exit(self):
		assignment = self._assignment(self.override_date)
		grace = self._grace(self.override_type)
		early_by = frappe.utils.add_to_date(
			assignment.end_datetime, minutes=-((grace.early_exit_grace_period or 0) + 5)
		)

		checkin = self._checkin(assignment, early_by, log_type="OUT")

		self.assertEqual(checkin.early_exit, 1)

	def test_leaving_at_the_override_s_end_is_not_an_early_exit(self):
		assignment = self._assignment(self.override_date)

		checkin = self._checkin(assignment, assignment.end_datetime, log_type="OUT")

		self.assertEqual(checkin.early_exit, 0)

	# ------------------------------------------------------- a default day is unchanged

	def test_a_default_day_is_benchmarked_against_the_default(self):
		assignment = self._assignment(self.default_date)

		self.assertEqual(assignment.shift_type, self.default_type)
		default_start = frappe.db.get_value("Shift Type", self.default_type, "start_time")
		self.assertEqual(assignment.start_datetime, get_datetime(f"{self.default_date} {default_start}"))

	def test_arriving_on_time_on_a_default_day_is_not_late(self):
		assignment = self._assignment(self.default_date)

		checkin = self._checkin(assignment, assignment.start_datetime)

		self.assertEqual(checkin.late_entry, 0)

	def test_arriving_late_on_a_default_day_is_still_late(self):
		assignment = self._assignment(self.default_date)
		grace = self._grace(self.default_type)
		if not grace.enable_entry_grace_period:
			self.skipTest(f"{self.default_type} has no entry grace period configured")
		late_by = frappe.utils.add_to_date(
			assignment.start_datetime, minutes=(grace.late_entry_grace_period or 0) + 5
		)

		checkin = self._checkin(assignment, late_by)

		self.assertEqual(checkin.late_entry, 1)

	def test_with_the_override_off_the_day_returns_to_the_default(self):
		self._set_override(False)
		assignment = self._assignment(self.override_date)

		self.assertEqual(assignment.shift_type, self.default_type)
