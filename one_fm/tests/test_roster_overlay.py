# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002591 AC1-AC4: who is actually on the bus today.

The generator builds cards from ``Employee.shift`` - the MASTER allocation - which
answers "whose post is this", not "who is travelling". The two part company constantly.

How leave really works here, confirmed in the code and against the live data rather than
assumed from the acceptance criteria:

* ``LeaveApplicationOverride.clear_employee_schedules`` DELETES the employee's Employee
  Schedule rows for the range, and ``close_shifts`` deletes their Shift Assignments.
* ``update_attendance`` then marks Attendance ``On Leave`` - 69,427 such rows exist.
* The employee stays ``Active`` with ``shift`` intact. Six employees were on approved
  leave and still carried a shift on the day this was written, so they were still being
  put on transportation cards while away.

That is why the overlay reads **Leave Application** and not the roster: the roster row for
a leave day does not exist to be read. It is also why no reliever in the database is
linked to a leave-covered schedule - the schedule they would point at was deleted - and
relief is instead recorded against a Day Off. Both are the same thing to a bus.

Nothing is stored. The overlay is recomputed for the date every time, so a leave range
ending restores the original rider by itself (AC3) with no expiry job to run.
"""

import itertools

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from one_fm.one_fm.doctype.transportation_shipment.roster_overlay import (
	absent_employees,
	apply_to_shift_map,
	relieving_assignments,
	reliever_context,
)


# A date far enough out that no real roster or leave row lands on it. The overlay reads
# the LIVE tables - there really are relievers working today - so a test that asserts
# "nothing changed" has to ask about a day nobody is scheduled on.
TEST_DATE = add_days(today(), 2500)

# FrappeTestCase rolls back per CLASS, not per test, so rows written by one test are still
# there for the next one and Employee Schedule refuses a second row for the same
# employee+date. Each test therefore gets a day of its own.
_DAY = itertools.count()


def _own_day():
	return add_days(TEST_DATE, next(_DAY) * 7)


def _active_employees(count, on_date):
	"""Real Active employees with nothing already rostered on ``on_date``.

	Two constraints meet here. Employee Schedule refuses to schedule anyone who is not
	Active, and creating employees on this bench is slow and hits a tabEmployee row-size
	wall - so the fixtures borrow real ones. But the roster is generated YEARS ahead (every
	date in 2033 already carries rows), so "a date far in the future" is not an empty one:
	whoever is already scheduled that day would collide with "already scheduled for X".
	"""
	taken = {
		row.employee
		for row in frappe.get_all("Employee Schedule", filters={"date": on_date},
								  fields=["employee"])
	}
	# ...and nobody who already has real approved leave anywhere near that day, or the
	# fixture's own leave would not be the one the overlay reports.
	window = (add_days(on_date, -30), add_days(on_date, 30))
	taken |= {
		row.employee
		for row in frappe.get_all(
			"Leave Application",
			filters={"docstatus": 1, "status": "Approved",
					 "from_date": ["<=", window[1]], "to_date": [">=", window[0]]},
			fields=["employee"])
	}
	rows = frappe.get_all("Employee", filters={"status": "Active"},
						  fields=["name"], limit=count + len(taken) + 20, order_by="name")
	free = [r.name for r in rows if r.name not in taken]
	if len(free) < count:
		raise AssertionError(f"need {count} Active employees free on {on_date}")
	return free[:count]


def _leave(employee, from_date, to_date, status="Approved", docstatus=1):
	doc = frappe.new_doc("Leave Application")
	doc.employee = employee
	doc.from_date = from_date
	doc.to_date = to_date
	doc.status = status
	doc.flags.ignore_mandatory = True
	doc.flags.ignore_links = True
	doc.flags.ignore_validate = True
	doc.insert(ignore_permissions=True)
	if docstatus == 1:
		frappe.db.set_value("Leave Application", doc.name, "docstatus", 1, update_modified=False)
	return doc.name


def _schedule(employee, date, **values):
	doc = frappe.new_doc("Employee Schedule")
	doc.employee = employee
	doc.date = date
	doc.employee_availability = values.pop("availability", "Working")
	doc.update(values)
	doc.flags.ignore_mandatory = True
	doc.flags.ignore_links = True
	doc.flags.ignore_validate = True
	doc.insert(ignore_permissions=True)
	return doc.name


class TestWhoIsAway(FrappeTestCase):
	"""AC1: an employee on approved leave is not on the bus."""

	def setUp(self):
		self.date = _own_day()
		self.emp = _active_employees(1, self.date)[0]

	def test_leave_covering_today_is_found_with_its_span(self):
		_leave(self.emp, add_days(self.date, -2), add_days(self.date, 3))

		away = absent_employees(self.date, [self.emp])

		self.assertIn(self.emp, away)
		self.assertEqual(str(away[self.emp][0]), add_days(self.date, -2))
		self.assertEqual(str(away[self.emp][1]), add_days(self.date, 3))

	def test_leave_that_has_not_started_does_not_count(self):
		_leave(self.emp, add_days(self.date, 1), add_days(self.date, 5))

		self.assertNotIn(self.emp, absent_employees(self.date, [self.emp]))

	def test_leave_that_has_ended_does_not_count(self):
		# AC3's reversion, from the other side: nothing expires the overlay because
		# nothing is stored - the range simply stops covering today.
		_leave(self.emp, add_days(self.date, -9), add_days(self.date, -1))

		self.assertNotIn(self.emp, absent_employees(self.date, [self.emp]))

	def test_the_first_and_last_day_are_both_leave(self):
		start = add_days(self.date, -4)
		_leave(self.emp, start, self.date)

		self.assertIn(self.emp, absent_employees(start, [self.emp]))
		self.assertIn(self.emp, absent_employees(self.date, [self.emp]))

	def test_an_unapproved_application_is_not_leave(self):
		_leave(self.emp, add_days(self.date, -1), add_days(self.date, 1), status="Open", docstatus=0)

		self.assertNotIn(self.emp, absent_employees(self.date, [self.emp]))

	def test_asking_about_nobody_asks_the_database_nothing(self):
		self.assertEqual(absent_employees(self.date, []), {})


class TestWhoIsCovering(FrappeTestCase):
	"""AC1/AC2: a reliever rides the run they are COVERING, not their own."""

	def setUp(self):
		self.date = _own_day()
		self.cover, self.away = _active_employees(2, self.date)

	def _pair(self, availability="Day Off", shift="SHIFT-COVERED"):
		original = _schedule(self.away, self.date, availability=availability,
							 employee_name="Away Person")
		_schedule(self.cover, self.date, availability="Working", shift=shift,
				  employee_name="Cover Person", is_relieving_schedule=1,
				  relieving_employee_schedule=original)
		return original

	def test_the_reliever_is_filed_under_the_shift_being_covered(self):
		self._pair(shift="SHIFT-COVERED")

		overlay = relieving_assignments(self.date)

		self.assertIn(self.cover, overlay)
		self.assertEqual(overlay[self.cover]["shift"], "SHIFT-COVERED")

	def test_the_covered_person_is_named_for_the_tag(self):
		self._pair()

		overlay = relieving_assignments(self.date)

		self.assertEqual(overlay[self.cover]["relieving_employee"], self.away)
		self.assertEqual(overlay[self.cover]["relieving_employee_name"], "Away Person")
		self.assertEqual(overlay[self.cover]["absence_reason"], "Day Off")

	def test_a_relieving_row_that_is_not_working_is_not_a_passenger(self):
		# A relieving row marked Day Off is a scheduling artefact, not somebody on a bus.
		original = _schedule(self.away, self.date, availability="Day Off")
		_schedule(self.cover, self.date, availability="Day Off", shift="SHIFT-COVERED",
				  is_relieving_schedule=1, relieving_employee_schedule=original)

		self.assertNotIn(self.cover, relieving_assignments(self.date))

	def test_a_dangling_back_link_still_puts_them_on_the_bus(self):
		# The covered schedule is deleted when the absence turns out to be leave, so the
		# link dangles. The reliever is still travelling; they just cannot be tagged.
		_schedule(self.cover, self.date, availability="Working", shift="SHIFT-COVERED",
				  is_relieving_schedule=1,
				  relieving_employee_schedule="does-not-exist")

		overlay = relieving_assignments(self.date)

		self.assertIn(self.cover, overlay)
		self.assertIsNone(overlay[self.cover]["relieving_employee"])

	def test_the_tooltip_context_carries_a_leave_span_when_there_is_one(self):
		self._pair()
		_leave(self.away, add_days(self.date, -1), add_days(self.date, 2))

		context = reliever_context(self.date)

		self.assertEqual(str(context[self.cover]["leave_from"]), add_days(self.date, -1))
		self.assertEqual(str(context[self.cover]["leave_to"]), add_days(self.date, 2))

	def test_no_leave_leaves_the_span_blank_rather_than_inventing_one(self):
		self._pair()

		context = reliever_context(self.date)

		self.assertIsNone(context[self.cover]["leave_from"])
		self.assertIsNone(context[self.cover]["leave_to"])
		self.assertEqual(context[self.cover]["absence_reason"], "Day Off")


class TestTheShiftMapIsRewritten(FrappeTestCase):
	"""What the generator actually consumes."""

	def setUp(self):
		self.date = _own_day()
		self.away, self.cover, self.other = _active_employees(3, self.date)

	def test_someone_on_leave_is_dropped(self):
		_leave(self.away, add_days(self.date, -1), add_days(self.date, 1))

		resolved = apply_to_shift_map({self.away: "SHIFT-X", self.other: "SHIFT-X"}, self.date)

		self.assertNotIn(self.away, resolved)
		self.assertEqual(resolved[self.other], "SHIFT-X")

	def test_a_reliever_is_added_under_the_covered_shift(self):
		original = _schedule(self.away, self.date, availability="Day Off")
		_schedule(self.cover, self.date, availability="Working", shift="SHIFT-COVERED",
				  is_relieving_schedule=1, relieving_employee_schedule=original)

		resolved = apply_to_shift_map({self.other: "SHIFT-X"}, self.date)

		self.assertEqual(resolved[self.cover], "SHIFT-COVERED")

	def test_a_relievers_own_master_shift_is_overridden(self):
		# AC4's shape: the bus they ride today is the post they are working, not the one
		# on their Employee record.
		original = _schedule(self.away, self.date, availability="Day Off")
		_schedule(self.cover, self.date, availability="Working", shift="SHIFT-COVERED",
				  is_relieving_schedule=1, relieving_employee_schedule=original)

		resolved = apply_to_shift_map({self.cover: "SHIFT-THEIR-OWN"}, self.date)

		self.assertEqual(resolved[self.cover], "SHIFT-COVERED")

	def test_the_callers_mapping_is_not_mutated(self):
		_leave(self.away, self.date, self.date)
		original = {self.away: "SHIFT-X"}

		apply_to_shift_map(original, self.date)

		self.assertEqual(original, {self.away: "SHIFT-X"})

	def test_an_ordinary_day_changes_nothing(self):
		before = {self.other: "SHIFT-X"}

		self.assertEqual(apply_to_shift_map(dict(before), self.date), before)
