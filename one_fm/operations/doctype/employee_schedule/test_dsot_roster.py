# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002437: a rejected double shift does not persist on the roster, and a new one can
be raised for the same day.

The two halves the story is really about:

  * the Roster Matrix stops rendering a shift cell for an overtime schedule that is
    waiting on the DSOT Approver or has been refused (AC 1.1, AC 1.3, AC 1.4, AC 1.5); and
  * re-rostering overtime for a day already refused puts the request back in front of the
    approver instead of silently leaving it rejected (AC 1.6).

Approving still lands on Active rather than on a state called "Approved" - Frappe allows
one workflow per doctype, and Active is both what the Shift Assignment job picks up and
what the suspension flow starts from. Confirmed with the process owner.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from one_fm.one_fm.page.roster.employee_map import (
	NOT_A_WORKED_SHIFT,
	CreateMap,
	get_schedule_state_filter,
)
from one_fm.operations.doctype.employee_schedule.employee_schedule import (
	ACTIVE,
	BASIC,
	DSOT_REJECTED,
	OVERTIME,
	PENDING_DSOT,
	WORKING,
	hold_overtime_for_approval,
)

SEEDED = "WI-002437-SEED-"


def _an_employee():
	return frappe.db.get_value("Employee", {"status": "Active"}, "name")


def _an_employee_who_is_not_leaving():
	"""One the controller will accept a far-future schedule for.

	validate_relieving_date refuses any date past the employee's leaving date, and the
	first active employee on this site has one - so a schedule 900 days out is refused
	before the rule under test is ever reached.
	"""
	return frappe.db.get_value(
		"Employee", {"status": "Active", "relieving_date": ["is", "not set"]}, "name"
	)


def _seed(suffix, roster_type=OVERTIME, workflow_state=ACTIVE, availability=WORKING, employee=None, date=None):
	"""A schedule row written the way the roster writes them - raw, no controller."""
	frappe.db.sql(
		"""INSERT INTO `tabEmployee Schedule`
		   (`name`, `employee`, `date`, `roster_type`, `employee_availability`,
		    `workflow_state`, `owner`, `modified_by`, `creation`, `modified`)
		   VALUES (%s, %s, %s, %s, %s, %s, 'Administrator', 'Administrator', NOW(), NOW())""",
		(SEEDED + suffix, employee, date, roster_type, availability, workflow_state),
	)
	return SEEDED + suffix


def _clear():
	frappe.db.sql("DELETE FROM `tabEmployee Schedule` WHERE name LIKE %s", SEEDED + "%")


def _rows_the_roster_would_render():
	"""The names the Roster Matrix's own WHERE clause leaves behind, over the seeded rows.

	The clause is asked for rather than copied, so a change to it is a change here too.
	"""
	return {
		row[0]
		for row in frappe.db.sql(
			f"""SELECT es.name FROM `tabEmployee Schedule` es
			    WHERE es.name LIKE %s AND {get_schedule_state_filter()}""",
			SEEDED + "%",
		)
	}


class TestTheRosterQueryUsesTheFilter(FrappeTestCase):
	"""Asked of the query the map actually builds - a filter nothing splices in would pass
	every other test in this file and change nothing on the roster."""

	def test_the_schedule_query_carries_it(self):
		query = CreateMap.schedule_query(
			frappe._dict(str_filter="1 = 1", employees="('_TEST')")
		)

		self.assertIn(get_schedule_state_filter(), query)

	def test_the_filter_is_valid_sql(self):
		frappe.db.sql(
			f"SELECT es.name FROM `tabEmployee Schedule` es WHERE {get_schedule_state_filter()} LIMIT 1"
		)

	def test_it_names_the_two_states_the_story_names(self):
		self.assertEqual(set(NOT_A_WORKED_SHIFT), {PENDING_DSOT, DSOT_REJECTED})

	def test_both_states_exist_on_the_workflow(self):
		"""Every one of these is a string comparison; a state named in the wrong case
		filters nothing."""
		workflow = frappe.db.get_value(
			"Workflow", {"document_type": "Employee Schedule", "is_active": 1}, "name"
		)
		if not workflow:
			self.skipTest("no active Employee Schedule workflow on this site")

		states = frappe.get_all(
			"Workflow Document State",
			filters={"parent": workflow, "parenttype": "Workflow"},
			pluck="state",
		)
		for state in NOT_A_WORKED_SHIFT:
			with self.subTest(state=state):
				self.assertIn(state, states)


class TestWhatTheRosterRenders(FrappeTestCase):
	def setUp(self):
		self.employee = _an_employee()
		if not self.employee:
			self.skipTest("no active employee on this site")
		self.date = add_days(today(), 60)
		_clear()

	def tearDown(self):
		_clear()

	def test_a_pending_double_shift_is_not_rendered(self):
		"""AC 1.1 - nobody has said yes to it yet, so it is not a shift on the roster."""
		_seed("PENDING", workflow_state=PENDING_DSOT, employee=self.employee, date=self.date)

		self.assertEqual(_rows_the_roster_would_render(), set())

	def test_a_rejected_double_shift_is_not_rendered(self):
		"""AC 1.3 and AC 1.4 - refused outright, or left unanswered until the shift ended."""
		_seed("REJECTED", workflow_state=DSOT_REJECTED, employee=self.employee, date=self.date)

		self.assertEqual(_rows_the_roster_would_render(), set())

	def test_an_approved_double_shift_is_rendered(self):
		"""AC 1.2 - approving lands on Active, and the cell comes back."""
		approved = _seed("ACTIVE", workflow_state=ACTIVE, employee=self.employee, date=self.date)

		self.assertEqual(_rows_the_roster_would_render(), {approved})

	def test_a_schedule_with_no_availability_is_not_rendered(self):
		"""AC 1.5's second half. No row here carries a blank one today; what this pins is
		that one never renders as a shift cell if anything ever writes it."""
		_seed("NOAVAIL", availability=None, employee=self.employee, date=self.date)

		self.assertEqual(_rows_the_roster_would_render(), set())

	def test_the_basic_shift_underneath_is_untouched(self):
		"""The employee is still working that day - only the double shift goes."""
		basic = _seed("BASIC", roster_type=BASIC, employee=self.employee, date=self.date)
		_seed("PENDING", workflow_state=PENDING_DSOT, employee=self.employee, date=self.date)

		self.assertEqual(_rows_the_roster_would_render(), {basic})

	def test_an_ordinary_schedule_with_no_state_at_all_is_rendered(self):
		"""A site without the suspension workflow has no workflow_state to read, and its
		roster has to keep working."""
		ordinary = _seed(
			"NOSTATE", roster_type=BASIC, workflow_state=None, employee=self.employee, date=self.date
		)

		self.assertEqual(_rows_the_roster_would_render(), {ordinary})


class TestOvertimeCanBeAskedForAgainAfterARejection(FrappeTestCase):
	"""AC 1.6. The roster names its rows "<date>_<employee>_<roster type>", so re-rostering
	overtime for a refused day writes over the same row - and its ON DUPLICATE KEY UPDATE
	does not touch workflow_state."""

	def setUp(self):
		self.employee = _an_employee()
		if not self.employee:
			self.skipTest("no active employee on this site")
		# Far enough out that the employee has no real roster there: the rule reads every
		# Basic schedule on the day, not only the seeded ones, so a date they are already
		# rostered on would make the "no basic shift" case untestable.
		# A day of its own: test_dsot_approval's roster-path class works on day 900, and
		# both ask what basic shifts the employee has that day.
		self.date = add_days(today(), 901)
		if frappe.db.exists("Employee Schedule", {"employee": self.employee, "date": self.date}):
			self.skipTest("the employee is already rostered on the test date")
		_clear()

	def tearDown(self):
		_clear()

	def _pair(self, overtime_state):
		_seed("BASIC", roster_type=BASIC, employee=self.employee, date=self.date)
		return _seed(
			"OT", roster_type=OVERTIME, workflow_state=overtime_state,
			employee=self.employee, date=self.date,
		)

	def _state(self, name):
		return frappe.db.get_value("Employee Schedule", name, "workflow_state")

	def test_a_rejected_request_goes_back_in_front_of_the_approver(self):
		overtime = self._pair(DSOT_REJECTED)

		self.assertEqual(hold_overtime_for_approval([overtime]), [overtime])
		self.assertEqual(self._state(overtime), PENDING_DSOT)

	def test_an_approved_one_is_still_not_dragged_back(self):
		"""Re-running the roster over the same day must not undo a decision that stands."""
		overtime = self._pair(ACTIVE)

		self.assertEqual(hold_overtime_for_approval([overtime]), [])
		self.assertEqual(self._state(overtime), ACTIVE)

	def test_one_already_pending_is_left_where_it_is(self):
		overtime = self._pair(PENDING_DSOT)

		self.assertEqual(hold_overtime_for_approval([overtime]), [])
		self.assertEqual(self._state(overtime), PENDING_DSOT)

	def test_it_is_still_validated_against_the_basic_shift(self):
		"""AC 1.6 asks for the new request to be checked against the employee's active
		Basic shift. Overtime on a day they are not already working is ordinary overtime
		and needs no approval - a rejected one included."""
		overtime = _seed(
			"OT", roster_type=OVERTIME, workflow_state=DSOT_REJECTED,
			employee=self.employee, date=self.date,
		)

		self.assertEqual(hold_overtime_for_approval([overtime]), [])
		self.assertEqual(self._state(overtime), DSOT_REJECTED)


class TestADoubleShiftRaisedThroughTheOrmReachesTheGate(FrappeTestCase):
	"""AC 1.6 end to end, on the path that was not working at all.

	The state used to be set on the document in before_insert, and Frappe's own workflow
	validation then refused the save: on an insert there is no before-state to transition
	from, so the first state is the only one a new document may carry. Every double shift
	raised through the ORM died with "Workflow State transition not allowed from Active to
	Pending DSOT Approval" - it never reached the approver, and the supervisor saw an
	error rather than a request.
	"""

	def setUp(self):
		self.employee = _an_employee_who_is_not_leaving()
		if not self.employee:
			self.skipTest("no active employee without a leaving date on this site")
		self.date = add_days(today(), 902)
		if frappe.db.exists("Employee Schedule", {"employee": self.employee, "date": self.date}):
			self.skipTest("the employee is already rostered on the test date")
		self.made = []
		_clear()

	def tearDown(self):
		for name in self.made:
			frappe.db.sql("DELETE FROM `tabEmployee Schedule` WHERE name = %s", name)
		_clear()

	def _insert_overtime(self):
		schedule = frappe.new_doc("Employee Schedule")
		schedule.employee = self.employee
		schedule.date = self.date
		schedule.roster_type = OVERTIME
		schedule.employee_availability = WORKING
		schedule.insert(ignore_permissions=True)
		self.made.append(schedule.name)
		return schedule

	def test_it_saves_and_lands_in_the_gate(self):
		_seed("BASIC", roster_type=BASIC, employee=self.employee, date=self.date)

		schedule = self._insert_overtime()

		self.assertEqual(
			frappe.db.get_value("Employee Schedule", schedule.name, "workflow_state"), PENDING_DSOT
		)

	def test_ordinary_overtime_is_left_active(self):
		"""Overtime on a day the employee is not already working needs nobody's approval,
		and must not be dragged into the gate."""
		schedule = self._insert_overtime()

		self.assertNotEqual(
			frappe.db.get_value("Employee Schedule", schedule.name, "workflow_state"), PENDING_DSOT
		)

	def test_the_pending_request_does_not_render_on_the_roster(self):
		"""AC 1.1, from the state a real save leaves behind rather than a seeded one."""
		_seed("BASIC", roster_type=BASIC, employee=self.employee, date=self.date)
		schedule = self._insert_overtime()

		rendered = {
			row[0]
			for row in frappe.db.sql(
				f"""SELECT es.name FROM `tabEmployee Schedule` es
				    WHERE es.employee = %s AND es.date = %s AND {get_schedule_state_filter()}""",
				(self.employee, self.date),
			)
		}

		self.assertNotIn(schedule.name, rendered)


class TestWhatTheShiftAssignmentJobPicksUp(FrappeTestCase):
	"""No Shift Assignment while a double shift waits, and one once it is Active.

	Asked of the job itself rather than of its source: overtime_shift_assignment hands the
	rows it selected to a background job, so the enqueue call is where they can be read.
	"""

	def setUp(self):
		self.employees = frappe.get_all("Employee", filters={"status": "Active"}, pluck="name", limit=3)
		if len(self.employees) < 3:
			self.skipTest("needs three active employees on this site")
		_clear()

	def tearDown(self):
		_clear()

	def _selected(self):
		import one_fm.api.tasks as tasks

		captured = {}
		original = frappe.enqueue
		frappe.enqueue = lambda *args, **kwargs: captured.setdefault("roster", kwargs.get("roster"))
		try:
			tasks.overtime_shift_assignment()
		finally:
			frappe.enqueue = original

		return {row.get("name") for row in (captured.get("roster") or [])}

	def _overtime_today(self, suffix, employee, workflow_state):
		name = _seed(
			suffix, roster_type=OVERTIME, workflow_state=workflow_state,
			employee=employee, date=today(),
		)
		# The job also filters is_replaced = 0, which a raw INSERT leaves NULL.
		frappe.db.set_value("Employee Schedule", name, "is_replaced", 0, update_modified=False)
		return name

	def test_a_pending_double_shift_is_not_given_one(self):
		pending = self._overtime_today("PENDING", self.employees[0], PENDING_DSOT)

		self.assertNotIn(pending, self._selected())

	def test_a_rejected_one_is_not_given_one(self):
		rejected = self._overtime_today("REJECTED", self.employees[1], DSOT_REJECTED)

		self.assertNotIn(rejected, self._selected())

	def test_an_approved_one_is(self):
		"""The other half - once the request is Active the job has to pick it up, or an
		approved double shift never becomes a Shift Assignment at all."""
		approved = self._overtime_today("ACTIVE", self.employees[2], ACTIVE)

		self.assertIn(approved, self._selected())


class TestApprovalDoesNotDuplicateAnAssignment(FrappeTestCase):
	"""Approving today's overtime raises the Shift Assignment straight away - but only if
	the job has not already made one, which it does every five minutes."""

	def setUp(self):
		self.employee = _an_employee()
		if not self.employee:
			self.skipTest("no active employee on this site")
		_clear()
		for existing in frappe.get_all(
			"Employee Schedule",
			filters={"employee": self.employee, "date": today(), "roster_type": OVERTIME},
			pluck="name",
		):
			frappe.db.sql("DELETE FROM `tabEmployee Schedule` WHERE name = %s", existing)

		self.schedule = frappe.new_doc("Employee Schedule")
		self.schedule.employee = self.employee
		self.schedule.date = today()
		self.schedule.roster_type = OVERTIME
		self.schedule.employee_availability = WORKING
		self.schedule.insert(ignore_permissions=True)

	def tearDown(self):
		frappe.db.sql("DELETE FROM `tabEmployee Schedule` WHERE name = %s", self.schedule.name)
		_clear()

	def _calls_to_the_builder(self):
		import one_fm.api.tasks as tasks

		calls = []
		original = tasks.create_overtime_shift_assignment
		tasks.create_overtime_shift_assignment = lambda *a, **k: calls.append(a)
		try:
			self.schedule.create_dsot_shift_assignment()
		finally:
			tasks.create_overtime_shift_assignment = original

		return calls

	def test_it_builds_one_when_there_is_none(self):
		self.assertEqual(len(self._calls_to_the_builder()), 1)

	def test_it_builds_nothing_when_one_already_exists(self):
		assignment = frappe.get_doc({
			"doctype": "Shift Assignment",
			"employee": self.employee,
			"start_date": today(),
			"roster_type": OVERTIME,
			"docstatus": 1,
		})
		assignment.db_insert()
		try:
			self.assertEqual(self._calls_to_the_builder(), [])
		finally:
			frappe.db.sql("DELETE FROM `tabShift Assignment` WHERE name = %s", assignment.name)
