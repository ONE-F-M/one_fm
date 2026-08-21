# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-001832: an Employee Schedule carries the Shift Type its date resolves to."""

import frappe
from frappe.tests.utils import FrappeTestCase

# Far enough out that the site has no real roster there. FrappeTestCase rolls back per
# class rather than per test, so a row one test inserts is still present for the next -
# _schedule clears the slot it is about to fill.
A_FRIDAY = "2027-01-01"
A_MONDAY = "2027-01-04"


def _a_shift_type(start, end):
	name = frappe.db.get_value("Shift Type", {"start_time": start, "end_time": end}, "name")
	if not name:
		raise frappe.DoesNotExistError(f"No Shift Type running {start}-{end} on this site")
	return name


def _an_operations_shift():
	"""An Active Operations Shift on this site, with its own posts and roles already in place.

	Taken from the site rather than created: Operations Shift autonames off a Service Type and
	an Operations Site, and its validation reaches into Operations Post, Operations Role and
	Employee.
	"""
	name = frappe.db.get_value(
		"Operations Shift", {"status": "Active", "shift_type": ["is", "set"]}, "name", order_by="creation asc"
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


class TestEmployeeScheduleOverride(FrappeTestCase):
	def setUp(self):
		self.employee = _an_active_employee()
		self.shift_name = _an_operations_shift()
		self.shift = frappe.get_doc("Operations Shift", self.shift_name)
		self.default_type = self.shift.shift_type

		# A Shift Type whose hours differ from this post's default, so the override is real.
		default_hours = frappe.db.get_value(
			"Shift Type", self.default_type, ["start_time", "end_time"], as_dict=True
		)
		self.override_type = frappe.db.get_value(
			"Shift Type",
			{"name": ["!=", self.default_type], "start_time": ["!=", default_hours.start_time]},
			"name",
			order_by="name asc",
		)
		if not self.override_type:
			self.skipTest("No second Shift Type on this site to override with")

	def _with_friday_override(self):
		self.shift.shift_timing_override_required = 1
		self.shift.set("operations_shift_timing", [])
		self.shift.append(
			"operations_shift_timing", {"day_of_week": "Friday", "shift_type": self.override_type}
		)
		self.shift.flags.ignore_permissions = True
		self.shift.save()
		frappe.clear_cache(doctype="Operations Shift")

	def _without_override(self):
		self.shift.shift_timing_override_required = 0
		self.shift.flags.ignore_permissions = True
		self.shift.save()
		frappe.clear_cache(doctype="Operations Shift")

	def _schedule(self, date, **kwargs):
		frappe.db.delete("Employee Schedule", {"employee": self.employee, "date": date})
		schedule = frappe.get_doc(
			{
				"doctype": "Employee Schedule",
				"employee": self.employee,
				"date": date,
				"shift": self.shift_name,
				"site": self.shift.site,
				"project": self.shift.project,
				"employee_availability": "Working",
				"shift_type": self.default_type,
				"roster_type": "Basic",
				**kwargs,
			}
		)
		schedule.flags.ignore_permissions = True
		schedule.insert()
		return schedule

	def test_a_friday_schedule_takes_the_override(self):
		self._with_friday_override()

		schedule = self._schedule(A_FRIDAY)

		self.assertEqual(schedule.shift_type, self.override_type)

	def test_the_datetimes_follow_the_override(self):
		self._with_friday_override()

		schedule = self._schedule(A_FRIDAY)

		start_time, end_time = frappe.db.get_value(
			"Shift Type", self.override_type, ["start_time", "end_time"]
		)
		self.assertEqual(str(schedule.start_datetime), f"{A_FRIDAY} {start_time}")
		self.assertTrue(str(schedule.end_datetime).endswith(str(end_time)))

	def test_a_non_override_day_keeps_the_default(self):
		self._with_friday_override()

		schedule = self._schedule(A_MONDAY)

		self.assertEqual(schedule.shift_type, self.default_type)

	def test_with_no_override_required_every_day_keeps_the_default(self):
		self._without_override()

		for date in (A_FRIDAY, A_MONDAY):
			self.assertEqual(self._schedule(date).shift_type, self.default_type)

	def test_a_blank_shift_type_is_filled_from_the_post(self):
		self._with_friday_override()

		schedule = self._schedule(A_FRIDAY, shift_type=None)

		self.assertEqual(schedule.shift_type, self.override_type)

	def test_the_field_is_a_mirror_of_the_post_not_a_caller_s_choice(self):
		# shift_type is read-only and declared fetch_from: shift.shift_type with no
		# fetch_if_empty, so Frappe replaces whatever a caller passes with the post's own type
		# before validate. The override therefore always wins, which is the field's existing
		# contract - it has only ever mirrored the post.
		self._with_friday_override()
		other = frappe.db.get_value(
			"Shift Type",
			{"name": ["not in", [self.default_type, self.override_type]]},
			"name",
			order_by="name asc",
		)
		if not other:
			self.skipTest("No third Shift Type on this site")

		schedule = self._schedule(A_FRIDAY, shift_type=other)

		self.assertEqual(schedule.shift_type, self.override_type)
		self.assertTrue(frappe.get_meta("Employee Schedule").get_field("shift_type").read_only)

	def test_a_day_off_row_is_not_given_a_shift_type(self):
		self._with_friday_override()

		schedule = self._schedule(A_FRIDAY, employee_availability="Day Off")

		self.assertFalse(schedule.shift_type)

	def test_a_row_with_no_operations_shift_is_untouched(self):
		self._with_friday_override()

		frappe.db.delete("Employee Schedule", {"employee": self.employee, "date": A_FRIDAY})
		schedule = frappe.get_doc(
			{
				"doctype": "Employee Schedule",
				"employee": self.employee,
				"date": A_FRIDAY,
				"employee_availability": "Day Off",
				"roster_type": "Basic",
			}
		)
		schedule.flags.ignore_permissions = True
		schedule.insert()

		self.assertFalse(schedule.shift)
