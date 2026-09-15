# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-001831: day-of-week shift timing overrides on an Operations Shift."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from one_fm.operations.doctype.operations_shift.operations_shift import (
	get_shift_timing_for_date,
	get_shift_type_for_date,
	resolve_shift_timing,
	shift_type_hours,
	shift_window,
)

# 2026-08-14 is a Friday, 2026-08-15 a Saturday, 2026-08-17 a Monday.
A_FRIDAY = "2026-08-14"
A_SATURDAY = "2026-08-15"
A_MONDAY = "2026-08-17"


def _a_shift_type(start, end):
	"""An existing Shift Type with the given hours.

	Taken from the site rather than created. one_fm autonames Shift Type from its own hours
	("Standard|Morning|08:00:00-17:00:00|9 hours") and refuses a second one with hours that
	already exist, so a fixture cannot choose its name and cannot make two types share hours.
	That is also why the "same hours as the default" validation can only be reached in
	practice by pointing an override row at the default Shift Type itself.
	"""
	name = frappe.db.get_value("Shift Type", {"start_time": start, "end_time": end}, "name")
	if not name:
		raise frappe.DoesNotExistError(f"No Shift Type running {start}-{end} on this site")
	return name


class TestShiftTimingOverride(FrappeTestCase):
	def setUp(self):
		self.default_type = _a_shift_type("08:00:00", "17:00:00")
		self.friday_type = _a_shift_type("12:00:00", "20:00:00")
		self.overnight_type = _a_shift_type("14:30:00", "02:30:00")

	def _shift(self, overrides=None, override_required=None):
		"""An unsaved Operations Shift, which is all the resolver and validation need.

		Built in memory rather than inserted: Operations Shift autonames off a Service Type
		and an Operations Site and its validation reaches into Operations Post, Operations
		Role and Employee, none of which this story touches.
		"""
		shift = frappe.get_doc(
			{
				"doctype": "Operations Shift",
				"shift_type": self.default_type,
				"shift_timing_override_required": (
					1 if override_required is None and overrides else (override_required or 0)
				),
				"operations_shift_timing": overrides or [],
			}
		)
		return shift

	# ------------------------------------------------------------------ resolver

	def test_with_the_flag_off_every_day_resolves_to_the_default(self):
		shift = self._shift(
			overrides=[{"day_of_week": "Friday", "shift_type": self.friday_type}],
			override_required=0,
		)

		for date in (A_FRIDAY, A_SATURDAY, A_MONDAY):
			timing = resolve_shift_timing(shift, date)
			self.assertEqual(timing.shift_type, self.default_type)
			self.assertFalse(timing.is_override)

	def test_the_override_day_resolves_to_the_override(self):
		shift = self._shift([{"day_of_week": "Friday", "shift_type": self.friday_type}])

		timing = resolve_shift_timing(shift, A_FRIDAY)

		self.assertEqual(timing.shift_type, self.friday_type)
		self.assertTrue(timing.is_override)
		self.assertEqual(str(timing.start_time), "12:00:00")
		self.assertEqual(str(timing.end_time), "20:00:00")

	def test_other_days_still_resolve_to_the_default(self):
		shift = self._shift([{"day_of_week": "Friday", "shift_type": self.friday_type}])

		for date in (A_SATURDAY, A_MONDAY):
			timing = resolve_shift_timing(shift, date)
			self.assertEqual(timing.shift_type, self.default_type)
			self.assertFalse(timing.is_override)

	def test_several_days_can_be_overridden_independently(self):
		shift = self._shift(
			[
				{"day_of_week": "Friday", "shift_type": self.friday_type},
				{"day_of_week": "Saturday", "shift_type": self.overnight_type},
			]
		)

		self.assertEqual(resolve_shift_timing(shift, A_FRIDAY).shift_type, self.friday_type)
		self.assertEqual(resolve_shift_timing(shift, A_SATURDAY).shift_type, self.overnight_type)
		self.assertEqual(resolve_shift_timing(shift, A_MONDAY).shift_type, self.default_type)

	def test_the_hours_come_from_the_shift_type_not_a_stale_copy(self):
		# The mirrored start_time/end_time on the row are fetch_from copies taken at save.
		shift = self._shift([{"day_of_week": "Friday", "shift_type": self.friday_type,
		                      "start_time": "01:00:00", "end_time": "02:00:00"}])

		timing = resolve_shift_timing(shift, A_FRIDAY)

		self.assertEqual(str(timing.start_time), "12:00:00")
		self.assertEqual(str(timing.end_time), "20:00:00")

	def test_a_date_object_resolves_the_same_as_a_string(self):
		shift = self._shift([{"day_of_week": "Friday", "shift_type": self.friday_type}])

		self.assertEqual(
			resolve_shift_timing(shift, getdate(A_FRIDAY)).shift_type,
			resolve_shift_timing(shift, A_FRIDAY).shift_type,
		)

	def test_the_helpers_need_both_a_shift_and_a_date(self):
		self.assertIsNone(get_shift_timing_for_date(None, A_FRIDAY))
		self.assertIsNone(get_shift_timing_for_date("Some Shift", None))
		self.assertIsNone(get_shift_type_for_date(None, A_FRIDAY))

	def test_a_shift_with_no_shift_type_resolves_to_no_hours(self):
		shift = self._shift()
		shift.shift_type = None

		timing = resolve_shift_timing(shift, A_MONDAY)

		self.assertIsNone(timing.shift_type)
		self.assertIsNone(timing.start_time)
		self.assertIsNone(timing.end_time)

	def test_shift_type_hours_reads_the_shift_type(self):
		self.assertEqual(
			[str(t) for t in shift_type_hours(self.friday_type)], ["12:00:00", "20:00:00"]
		)
		self.assertIsNone(shift_type_hours(None))

	# ------------------------------------------------------------- shift window

	def test_a_day_shift_starts_and_ends_on_the_same_date(self):
		shift = self._shift()
		timing = resolve_shift_timing(shift, A_MONDAY)
		start, end = shift_window(A_MONDAY, timing)

		self.assertEqual(start, f"{A_MONDAY} {timing.start_time}")
		self.assertEqual(end, f"{A_MONDAY} {timing.end_time}")

	def test_an_overnight_shift_ends_the_next_day(self):
		shift = self._shift([{"day_of_week": "Friday", "shift_type": self.overnight_type}])
		start, end = shift_window(A_FRIDAY, resolve_shift_timing(shift, A_FRIDAY))

		self.assertTrue(start.startswith(A_FRIDAY))
		self.assertTrue(end.startswith(A_SATURDAY))

	# -------------------------------------------------------------- validation

	def test_the_same_day_twice_is_blocked(self):
		shift = self._shift(
			[
				{"day_of_week": "Friday", "shift_type": self.friday_type},
				{"day_of_week": "Friday", "shift_type": self.overnight_type},
			]
		)

		with self.assertRaises(frappe.ValidationError):
			shift.validate_shift_timing_overrides()

	def test_the_same_day_twice_is_blocked_even_with_different_timings(self):
		# Supriya's rule: a day may appear once, whatever hours the two rows carry.
		shift = self._shift(
			[
				{"day_of_week": "Saturday", "shift_type": self.friday_type},
				{"day_of_week": "Saturday", "shift_type": self.overnight_type},
			]
		)

		with self.assertRaises(frappe.ValidationError):
			shift.validate_shift_timing_overrides()

	def test_an_override_with_the_default_s_own_hours_is_blocked(self):
		shift = self._shift([{"day_of_week": "Friday", "shift_type": self.default_type}])

		with self.assertRaises(frappe.ValidationError):
			shift.validate_shift_timing_overrides()

	def test_an_override_that_differs_is_accepted(self):
		shift = self._shift([{"day_of_week": "Friday", "shift_type": self.friday_type}])

		shift.validate_shift_timing_overrides()

	def test_different_days_with_different_timings_are_accepted(self):
		shift = self._shift(
			[
				{"day_of_week": "Friday", "shift_type": self.friday_type},
				{"day_of_week": "Saturday", "shift_type": self.overnight_type},
			]
		)

		shift.validate_shift_timing_overrides()

	def test_nothing_is_validated_while_the_flag_is_off(self):
		# Rows are kept, not cleared, so a configuration switched off and on again survives -
		# and while it is off it cannot be in the way.
		shift = self._shift(
			overrides=[
				{"day_of_week": "Friday", "shift_type": self.default_type},
				{"day_of_week": "Friday", "shift_type": self.default_type},
			],
			override_required=0,
		)

		shift.validate_shift_timing_overrides()

	def test_the_table_is_required_once_the_flag_is_on(self):
		field = frappe.get_meta("Operations Shift").get_field("operations_shift_timing")
		self.assertEqual(field.mandatory_depends_on, "eval:doc.shift_timing_override_required==1")
		self.assertEqual(field.depends_on, "eval:doc.shift_timing_override_required==1")

	def test_the_day_select_offers_every_day_of_the_week(self):
		options = frappe.get_meta("Operations Shift Timing").get_field("day_of_week").options
		for day in ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"):
			self.assertIn(day, options.split("\n"))

	def test_the_day_names_match_what_python_produces(self):
		# The resolver matches the stored day against getdate(date).strftime("%A").
		options = frappe.get_meta("Operations Shift Timing").get_field("day_of_week").options.split("\n")
		for date in (A_FRIDAY, A_SATURDAY, A_MONDAY):
			self.assertIn(getdate(date).strftime("%A"), options)
