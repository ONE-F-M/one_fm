# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002019: clearing an exiting employee's roster past their relieving date."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, today

from one_fm.overrides.employee import delete_employee_schedules_from


def _an_operations_shift():
	"""An Active Operations Shift, as a plain dict of the three fields a schedule needs.

	Read with db.get_value rather than loaded as a document: this story has nothing to do
	with Operations Shift's controller, and not loading it keeps the test independent of
	whatever that controller currently requires.
	"""
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


class TestDeletePostRelievingSchedules(FrappeTestCase):
	def setUp(self):
		self.employee = _an_active_employee()
		self.shift = _an_operations_shift()
		self.shift_name = self.shift.name

		# Well clear of anything the site has really rostered.
		self.relieving_date = add_days(today(), 40)
		self.before = add_days(self.relieving_date, -1)
		self.on = self.relieving_date
		self.after = add_days(self.relieving_date, 1)
		self.well_after = add_days(self.relieving_date, 10)

		for date in (self.before, self.on, self.after, self.well_after):
			frappe.db.delete("Employee Schedule", {"employee": self.employee, "date": date})

	def _schedule(self, date):
		schedule = frappe.get_doc({
			"doctype": "Employee Schedule",
			"employee": self.employee,
			"date": date,
			"shift": self.shift_name,
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

	# --------------------------------------------------------------- the boundary

	def test_the_boundary_is_inclusive_of_the_date_given(self):
		self._schedule(self.after)
		self._schedule(self.well_after)

		delete_employee_schedules_from(self.employee, self.after)

		self.assertFalse(self._exists(self.after))
		self.assertFalse(self._exists(self.well_after))

	def test_earlier_schedules_are_left_alone(self):
		self._schedule(self.before)
		self._schedule(self.on)
		self._schedule(self.after)

		delete_employee_schedules_from(self.employee, self.after)

		self.assertTrue(self._exists(self.before))
		self.assertTrue(self._exists(self.on))
		self.assertFalse(self._exists(self.after))

	def test_the_relieving_date_itself_is_a_working_day(self):
		# The employee works their last day; only what follows it is cleared.
		self._schedule(self.on)
		self._schedule(self.after)

		delete_employee_schedules_from(self.employee, add_days(getdate(self.relieving_date), 1))

		self.assertTrue(self._exists(self.on))
		self.assertFalse(self._exists(self.after))

	def test_another_employee_is_untouched(self):
		other = frappe.db.get_value(
			"Employee",
			{"status": "Active", "name": ["!=", self.employee]},
			"name",
			order_by="creation asc",
		)
		if not other:
			self.skipTest("Only one active employee on this site")
		frappe.db.delete("Employee Schedule", {"employee": other, "date": self.after})
		theirs = frappe.get_doc({
			"doctype": "Employee Schedule",
			"employee": other,
			"date": self.after,
			"shift": self.shift_name,
			"site": self.shift.site,
			"project": self.shift.project,
			"employee_availability": "Working",
			"shift_type": self.shift.shift_type,
			"roster_type": "Basic",
		})
		theirs.flags.ignore_permissions = True
		theirs.insert()

		delete_employee_schedules_from(self.employee, self.after)

		self.assertTrue(frappe.db.exists("Employee Schedule", theirs.name))

	# ------------------------------------------------- what the caller gets back

	def test_it_reports_the_projects_it_emptied(self):
		self._schedule(self.after)

		projects = delete_employee_schedules_from(self.employee, self.after)

		self.assertEqual(projects, [self.shift.project])

	def test_nothing_to_delete_reports_nothing(self):
		self.assertEqual(delete_employee_schedules_from(self.employee, self.after), [])

	def test_projects_are_reported_once_each(self):
		self._schedule(self.after)
		self._schedule(self.well_after)

		projects = delete_employee_schedules_from(self.employee, self.after)

		self.assertEqual(len(projects), len(set(projects)))

	# ------------------------------------------------------------- the trigger

	def test_setting_a_relieving_date_queues_the_cleanup(self):
		self._schedule(self.after)
		employee = frappe.get_doc("Employee", self.employee)
		employee.relieving_date = self.relieving_date

		enqueued = []
		original = frappe.enqueue

		def capture(method, **kwargs):
			enqueued.append((method, kwargs))
			return None

		frappe.enqueue = capture
		try:
			employee.clear_schedules()
		finally:
			frappe.enqueue = original

		self.assertEqual(len(enqueued), 1)
		method, kwargs = enqueued[0]
		self.assertIs(method, delete_employee_schedules_from)
		self.assertEqual(kwargs["employee"], self.employee)
		self.assertEqual(getdate(kwargs["from_date"]), getdate(self.after))

	def test_no_relieving_date_queues_nothing(self):
		# The old version interpolated None into the comparison and deleted nothing while
		# reporting success. Doing nothing deliberately is the same outcome, said honestly.
		employee = frappe.get_doc("Employee", self.employee)
		employee.relieving_date = None
		employee.status = "Left"

		enqueued = []
		original = frappe.enqueue
		frappe.enqueue = lambda method, **kwargs: enqueued.append(method)
		try:
			employee.clear_schedules()
		finally:
			frappe.enqueue = original

		self.assertEqual(enqueued, [])

	def test_an_unchanged_employee_queues_nothing(self):
		employee = frappe.get_doc("Employee", self.employee)

		enqueued = []
		original = frappe.enqueue
		frappe.enqueue = lambda method, **kwargs: enqueued.append(method)
		try:
			employee.clear_schedules()
		finally:
			frappe.enqueue = original

		self.assertEqual(enqueued, [])
