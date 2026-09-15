# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-001833: a Shift Assignment carries the Shift Type its own date resolves to."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days

A_FRIDAY = "2027-01-01"
A_MONDAY = "2027-01-04"


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


class TestShiftAssignmentTimingOverride(FrappeTestCase):
	def setUp(self):
		self.employee = _an_active_employee()
		self.shift_name = _an_operations_shift()
		self.shift = frappe.get_doc("Operations Shift", self.shift_name)
		self.default_type = self.shift.shift_type

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

		self.shift.shift_timing_override_required = 1
		self.shift.set("operations_shift_timing", [])
		self.shift.append(
			"operations_shift_timing", {"day_of_week": "Friday", "shift_type": self.override_type}
		)
		self.shift.flags.ignore_permissions = True
		self.shift.save()
		frappe.clear_cache(doctype="Operations Shift")

	def _assignment(self, start_date, **kwargs):
		"""An unsaved Shift Assignment, validated rather than inserted.

		validate() is where the resolution happens and is all these criteria are about;
		inserting drags in the overlap checks against whatever the site already has rostered
		for this employee.
		"""
		assignment = frappe.get_doc(
			{
				"doctype": "Shift Assignment",
				"employee": self.employee,
				"company": frappe.defaults.get_user_default("company"),
				"shift": self.shift_name,
				"shift_type": self.default_type,
				"start_date": start_date,
				"status": "Active",
				**kwargs,
			}
		)
		assignment.apply_shift_timing_override()
		return assignment

	def test_a_friday_assignment_takes_the_override(self):
		self.assertEqual(self._assignment(A_FRIDAY).shift_type, self.override_type)

	def test_a_non_override_day_keeps_the_default(self):
		self.assertEqual(self._assignment(A_MONDAY).shift_type, self.default_type)

	def test_the_datetimes_follow_the_resolved_shift_type(self):
		assignment = self._assignment(A_FRIDAY)
		assignment.set_datetime()

		start_time = frappe.db.get_value("Shift Type", self.override_type, "start_time")
		self.assertEqual(str(assignment.start_datetime), f"{A_FRIDAY} {start_time}")

	def test_the_classification_follows_the_resolved_shift_type(self):
		assignment = self._assignment(A_FRIDAY)

		self.assertEqual(
			assignment.shift_classification,
			frappe.db.get_value("Shift Type", self.override_type, "shift_type"),
		)

	def test_the_classification_matches_the_default_on_a_default_day(self):
		assignment = self._assignment(A_MONDAY)

		self.assertEqual(
			assignment.shift_classification,
			frappe.db.get_value("Shift Type", self.default_type, "shift_type"),
		)

	def test_a_blank_shift_type_is_filled_from_the_post(self):
		self.assertEqual(self._assignment(A_FRIDAY, shift_type=None).shift_type, self.override_type)

	def test_a_deliberately_chosen_shift_type_survives(self):
		# Unlike Employee Schedule.shift_type this field is not a fetch_from mirror, so a
		# caller's choice is a real choice - an event or overtime assignment runs its own hours.
		other = frappe.db.get_value(
			"Shift Type",
			{"name": ["not in", [self.default_type, self.override_type]]},
			"name",
			order_by="name asc",
		)
		if not other:
			self.skipTest("No third Shift Type on this site")

		self.assertEqual(self._assignment(A_FRIDAY, shift_type=other).shift_type, other)

	def test_a_multi_day_assignment_is_left_alone(self):
		# One assignment holds one Shift Type; a range covering both an override day and a
		# default day has no single right answer, and Shift Request splits those by date.
		assignment = self._assignment(A_FRIDAY, end_date=add_days(A_FRIDAY, 3))

		self.assertEqual(assignment.shift_type, self.default_type)

	def test_a_single_day_range_still_resolves(self):
		assignment = self._assignment(A_FRIDAY, end_date=A_FRIDAY)

		self.assertEqual(assignment.shift_type, self.override_type)

	def test_nothing_happens_without_an_operations_shift(self):
		assignment = self._assignment(A_FRIDAY, shift=None)

		self.assertEqual(assignment.shift_type, self.default_type)

	def test_the_default_is_kept_once_the_override_flag_is_off(self):
		self.shift.shift_timing_override_required = 0
		self.shift.flags.ignore_permissions = True
		self.shift.save()
		frappe.clear_cache(doctype="Operations Shift")

		self.assertEqual(self._assignment(A_FRIDAY).shift_type, self.default_type)
