# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002018: clearing the roster of an employee who did not come back from leave."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, today

from one_fm.overrides.employee import (
	NOT_RETURNED_FROM_LEAVE,
	clear_schedules_for_non_return,
	delete_employee_schedules_from,
	latest_resumption_date,
)


def _an_operations_shift():
	shift = frappe.db.get_value(
		"Operations Shift",
		{"status": "Active", "shift_type": ["is", "set"]},
		["name", "site", "project", "shift_type"],
		order_by="creation asc",
		as_dict=True,
	)
	if not shift:
		raise frappe.DoesNotExistError("No active Operations Shift on this site to test against")
	return shift


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


class TestDeleteSchedulesNotReturned(FrappeTestCase):
	def setUp(self):
		self.employee = _an_active_employee()
		self.shift = _an_operations_shift()

		self.resumption_date = add_days(today(), 30)
		self.before = add_days(self.resumption_date, -1)
		self.on = self.resumption_date
		self.after = add_days(self.resumption_date, 1)
		self.well_after = add_days(self.resumption_date, 20)

		for date in (self.before, self.on, self.after, self.well_after):
			frappe.db.delete("Employee Schedule", {"employee": self.employee, "date": date})

	def _schedule(self, date):
		schedule = frappe.get_doc({
			"doctype": "Employee Schedule",
			"employee": self.employee,
			"date": date,
			"shift": self.shift.name,
			"site": self.shift.site,
			"project": self.shift.project,
			"employee_availability": "Working",
			"shift_type": self.shift.shift_type,
			"roster_type": "Basic",
		})
		schedule.flags.ignore_permissions = True
		schedule.insert()
		return schedule

	def _exists(self, date):
		return bool(frappe.db.exists("Employee Schedule", {"employee": self.employee, "date": date}))

	# ------------------------------------------------- the date it clears from

	def test_the_resumption_date_itself_is_cleared(self):
		# The first day they were expected and did not appear is a day nobody will work.
		self._schedule(self.on)
		self._schedule(self.after)

		delete_employee_schedules_from(self.employee, self.resumption_date)

		self.assertFalse(self._exists(self.on))
		self.assertFalse(self._exists(self.after))

	def test_days_they_were_legitimately_on_leave_are_kept(self):
		# The old rule cleared a fixed seven days from today, which removed days before the
		# resumption date that nobody has any reason to re-staff.
		self._schedule(self.before)
		self._schedule(self.on)

		delete_employee_schedules_from(self.employee, self.resumption_date)

		self.assertTrue(self._exists(self.before))
		self.assertFalse(self._exists(self.on))

	def test_everything_past_the_seventh_day_is_cleared_too(self):
		# The old rule stopped after seven days and left the rest rostered to someone who is
		# not coming back.
		self._schedule(self.well_after)

		delete_employee_schedules_from(self.employee, self.resumption_date)

		self.assertFalse(self._exists(self.well_after))

	# --------------------------------------------------- finding the resumption date

	def test_it_reads_the_latest_approved_leave_application(self):
		found = latest_resumption_date(self.employee)
		expected = frappe.db.get_value(
			"Leave Application",
			{
				"employee": self.employee,
				"status": "Approved",
				"docstatus": 1,
				"resumption_date": ["is", "set"],
			},
			"resumption_date",
			order_by="to_date desc, modified desc",
		)

		self.assertEqual(found, expected)

	def test_an_employee_with_no_such_leave_gets_no_date(self):
		employee_without = frappe.db.sql(
			"""
			SELECT e.name FROM `tabEmployee` e
			WHERE e.status = 'Active'
			AND NOT EXISTS (
				SELECT 1 FROM `tabLeave Application` la
				WHERE la.employee = e.name AND la.status = 'Approved'
				AND la.docstatus = 1 AND la.resumption_date IS NOT NULL
			)
			LIMIT 1
			""",
			as_dict=True,
		)
		if not employee_without:
			self.skipTest("Every active employee on this site has a resumption date")

		self.assertIsNone(latest_resumption_date(employee_without[0].name))

	# ------------------------------------------------------------- the queued job

	def test_the_job_clears_and_then_rechecks(self):
		self._schedule(self.on)
		called = []
		import one_fm.operations.doctype.post_scheduler_checker.post_scheduler_checker as checker

		original = checker.schedule_roster_checker
		checker.schedule_roster_checker = lambda projects=None: called.append(projects)
		try:
			clear_schedules_for_non_return(self.employee, self.resumption_date)
		finally:
			checker.schedule_roster_checker = original

		self.assertFalse(self._exists(self.on))
		self.assertEqual(called, [[self.shift.project]])

	def test_nothing_deleted_means_no_checker_run(self):
		called = []
		import one_fm.operations.doctype.post_scheduler_checker.post_scheduler_checker as checker

		original = checker.schedule_roster_checker
		checker.schedule_roster_checker = lambda projects=None: called.append(projects)
		try:
			clear_schedules_for_non_return(self.employee, self.resumption_date)
		finally:
			checker.schedule_roster_checker = original

		self.assertEqual(called, [])

	# ---------------------------------------------------------------- the trigger

	def test_the_status_change_queues_the_cleanup(self):
		employee = frappe.get_doc("Employee", self.employee)
		if not latest_resumption_date(self.employee):
			self.skipTest("This employee has no approved leave carrying a resumption date")

		enqueued = []
		original = frappe.enqueue
		frappe.enqueue = lambda method, **kwargs: enqueued.append((method, kwargs))
		try:
			employee.clear_schedules_for_non_return()
		finally:
			frappe.enqueue = original

		self.assertEqual(len(enqueued), 1)
		method, kwargs = enqueued[0]
		self.assertIs(method, clear_schedules_for_non_return)
		self.assertEqual(kwargs["employee"], self.employee)
		self.assertEqual(
			getdate(kwargs["from_date"]), getdate(latest_resumption_date(self.employee))
		)

	def test_no_resumption_date_queues_nothing_and_says_so(self):
		employee_without = frappe.db.sql(
			"""
			SELECT e.name FROM `tabEmployee` e
			WHERE e.status = 'Active'
			AND NOT EXISTS (
				SELECT 1 FROM `tabLeave Application` la
				WHERE la.employee = e.name AND la.status = 'Approved'
				AND la.docstatus = 1 AND la.resumption_date IS NOT NULL
			)
			LIMIT 1
			""",
			as_dict=True,
		)
		if not employee_without:
			self.skipTest("Every active employee on this site has a resumption date")

		employee = frappe.get_doc("Employee", employee_without[0].name)
		before = frappe.db.count("Error Log")

		enqueued = []
		original = frappe.enqueue
		frappe.enqueue = lambda method, **kwargs: enqueued.append(method)
		try:
			employee.clear_schedules_for_non_return()
		finally:
			frappe.enqueue = original

		self.assertEqual(enqueued, [])
		# Silence would look identical to a cleanup that ran, so the reason is recorded.
		self.assertGreater(frappe.db.count("Error Log"), before)

	def test_the_status_is_spelled_the_way_the_app_defines_it(self):
		"""The constant matches the option one_fm's own property setter installs.

		Asserted against the definition in code rather than against frappe.get_meta, because
		the option reaches the Select through a property setter and a site whose property
		setters have not been applied yet would fail on its own configuration rather than on
		anything this story changed. A mismatch here, by contrast, means the trigger below can
		never fire - the comparison would silently never match.
		"""
		from one_fm.custom.property_setter.employee import get_employee_properties

		status_options = [
			entry["value"]
			for entry in get_employee_properties()
			if entry["field_name"] == "status" and entry["property"] == "options"
		]

		self.assertTrue(status_options, "no options property setter defined for Employee.status")
		self.assertIn(NOT_RETURNED_FROM_LEAVE, status_options[0].split("\n"))

	def test_the_checker_still_runs_over_everything_when_unfiltered(self):
		# The scheduled job calls it with no arguments and must keep its old behaviour.
		import inspect

		from one_fm.operations.doctype.post_scheduler_checker.post_scheduler_checker import (
			schedule_roster_checker,
		)

		signature = inspect.signature(schedule_roster_checker)
		self.assertIsNone(signature.parameters["projects"].default)
