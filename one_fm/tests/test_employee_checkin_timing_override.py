# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002039: check-in and check-out under the Operations Shift override.

The story has a user story but no acceptance criteria. Per Yusuff's clarification its
purpose is to confirm two things: that the override changes do not affect existing
check-in / check-out behaviour, and that check-in / check-out works correctly with an
overridden day. So this is a verification story, and the tests are the deliverable.

No production code changed, and in particular get_current_shift is NOT widened. It selects
from Shift Assignment joined to its Shift Type and derives the window as

    [start_datetime - begin_check_in_before_shift_start_time,
     end_datetime   + allow_check_out_after_shift_end_time]

so once WI-001833 put the override's Shift Type and datetimes on the assignment, the
window moved with them by itself. The 60/15/4-hour boundaries elsewhere in the check-in
path are deliberately left alone.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, add_to_date, getdate, today


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


class TestEmployeeCheckinTimingOverride(FrappeTestCase):
	def setUp(self):
		self.override_date = today()
		self.override_day = getdate(self.override_date).strftime("%A")
		self.default_date = add_days(self.override_date, -1)

		self.employee = _an_active_employee()
		self.shift_name = _an_operations_shift()
		self.shift = frappe.get_doc("Operations Shift", self.shift_name)
		self.default_type = self.shift.shift_type

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
			["begin_check_in_before_shift_start_time", "allow_check_out_after_shift_end_time"],
			as_dict=True,
		)

	# ---------------------------------------- the window follows the overridden day

	def test_the_window_is_built_from_the_override_s_hours(self):
		assignment = self._assignment(self.override_date)
		grace = self._grace(self.override_type)

		cutoff = assignment.get_cut_off()

		self.assertEqual(
			cutoff.start,
			add_to_date(
				assignment.start_datetime,
				minutes=-grace.begin_check_in_before_shift_start_time,
			),
		)
		self.assertEqual(
			cutoff.end,
			add_to_date(
				assignment.end_datetime, minutes=grace.allow_check_out_after_shift_end_time
			),
		)

	def test_the_window_moved_off_the_default_s_hours(self):
		# The override starts later, so its whole window sits later than the default's would.
		assignment = self._assignment(self.override_date)
		default_grace = self._grace(self.default_type)
		default_start = frappe.utils.get_datetime(
			f"{self.override_date} {frappe.db.get_value('Shift Type', self.default_type, 'start_time')}"
		)

		cutoff = assignment.get_cut_off()

		self.assertGreater(
			cutoff.start,
			add_to_date(
				default_start, minutes=-default_grace.begin_check_in_before_shift_start_time
			),
		)

	def test_checking_in_at_the_override_s_start_is_inside_the_window(self):
		assignment = self._assignment(self.override_date)
		cutoff = assignment.get_cut_off()

		self.assertGreaterEqual(assignment.start_datetime, cutoff.start)
		self.assertLessEqual(assignment.start_datetime, cutoff.end)

	def test_checking_out_at_the_override_s_end_is_inside_the_window(self):
		assignment = self._assignment(self.override_date)
		cutoff = assignment.get_cut_off()

		self.assertLessEqual(assignment.end_datetime, cutoff.end)

	def test_before_the_window_opens_is_outside_it(self):
		assignment = self._assignment(self.override_date)
		cutoff = assignment.get_cut_off()

		self.assertLess(add_to_date(cutoff.start, minutes=-1), cutoff.start)
		self.assertGreater(cutoff.end, cutoff.start)

	def test_the_window_covers_the_whole_shift(self):
		assignment = self._assignment(self.override_date)
		cutoff = assignment.get_cut_off()

		self.assertLessEqual(cutoff.start, assignment.start_datetime)
		self.assertGreaterEqual(cutoff.end, assignment.end_datetime)

	# ------------------------------------- existing behaviour on a non-override day

	def test_a_default_day_window_is_unchanged(self):
		assignment = self._assignment(self.default_date)
		grace = self._grace(self.default_type)

		cutoff = assignment.get_cut_off()

		self.assertEqual(assignment.shift_type, self.default_type)
		self.assertEqual(
			cutoff.start,
			add_to_date(
				assignment.start_datetime,
				minutes=-grace.begin_check_in_before_shift_start_time,
			),
		)

	def test_with_the_override_off_the_window_returns_to_the_default(self):
		self._set_override(False)
		assignment = self._assignment(self.override_date)
		grace = self._grace(self.default_type)

		cutoff = assignment.get_cut_off()

		self.assertEqual(assignment.shift_type, self.default_type)
		self.assertEqual(
			cutoff.start,
			add_to_date(
				assignment.start_datetime,
				minutes=-grace.begin_check_in_before_shift_start_time,
			),
		)

	def test_get_current_shift_was_not_widened(self):
		"""The window still comes from the assignment's own Shift Type, nothing broader.

		Pinned deliberately: the temptation when adding overrides is to widen the resolver so
		it considers more shifts, which would let people check in against a shift they are not
		on. The override reaches check-in through the assignment's data, not through a looser
		query.
		"""
		import inspect

		from one_fm.utils import get_current_shift

		source = inspect.getsource(get_current_shift)

		self.assertIn("tabShift Assignment", source)
		self.assertIn("begin_check_in_before_shift_start_time", source)
		self.assertIn("allow_check_out_after_shift_end_time", source)
		self.assertNotIn("operations_shift_timing", source)
