# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002437 follow-up: the background jobs that must not act on an unworked double shift.

The Shift Assignment side was settled by the story itself (test_dsot_roster). This file is
about everything else that reads Employee Schedule on a schedule and draws a conclusion
from it - a checker record against a supervisor, a filled post, a manpower figure, a seat
on a bus, a missed-assignment email. A double shift waiting on the DSOT Approver is not
evidence of any of those, and a rejected one never will be.

The rule is one pair of states and three shapes of query - ORM filters, Query Builder,
raw SQL - so the shapes are pinned here as well as the jobs, and the NULL case with them:
the roster writes its rows with a raw INSERT that never lists workflow_state, so a
schedule really can carry none, and a plain SQL NOT IN would drop every one of them.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from one_fm.one_fm.page.roster.employee_map import NOT_A_WORKED_SHIFT as ROSTER_STATES
from one_fm.operations.doctype.employee_schedule.employee_schedule import (
	ACTIVE,
	BASIC,
	DSOT_REJECTED,
	NOT_A_WORKED_SHIFT,
	OVERTIME,
	PENDING_DSOT,
	WORKING,
	has_workflow_state_column,
	worked_shift_criterion,
	worked_shift_filters,
	worked_shift_sql,
)

SEEDED = "WI-002437-BG-"


def _seed(suffix, workflow_state=ACTIVE, roster_type=OVERTIME, employee=None, date=None, shift=None):
	"""A schedule row written the way the roster writes them - raw, no controller.

	workflow_state is set with a second statement rather than in the INSERT so that None
	really means "the column was never written", which is the case the guards have to
	survive.
	"""
	name = SEEDED + suffix
	frappe.db.sql(
		"""INSERT INTO `tabEmployee Schedule`
		   (`name`, `employee`, `date`, `roster_type`, `employee_availability`, `shift`,
		    `is_replaced`, `owner`, `modified_by`, `creation`, `modified`)
		   VALUES (%s, %s, %s, %s, %s, %s, 0, 'Administrator', 'Administrator', NOW(), NOW())""",
		(name, employee, date, roster_type, WORKING, shift),
	)
	if workflow_state is not None:
		frappe.db.set_value("Employee Schedule", name, "workflow_state", workflow_state, update_modified=False)
	return name


def _clear():
	frappe.db.sql("DELETE FROM `tabEmployee Schedule` WHERE name LIKE %s", SEEDED + "%")


def _names_left(where):
	return {
		row[0]
		for row in frappe.db.sql(
			f"SELECT es.name FROM `tabEmployee Schedule` es WHERE es.name LIKE %s AND {where}",
			SEEDED + "%",
		)
	}


class TestTheRuleItself(FrappeTestCase):
	def test_it_names_the_two_states_the_story_names(self):
		self.assertEqual(set(NOT_A_WORKED_SHIFT), {PENDING_DSOT, DSOT_REJECTED})

	def test_the_roster_matrix_uses_the_same_pair(self):
		"""employee_map keeps its own copy, because its filter is a raw-SQL fragment built
		for the roster's own alias. Two copies of a pair of state names is one rename away
		from the roster and the background jobs disagreeing about what counts as worked."""
		self.assertEqual(set(ROSTER_STATES), set(NOT_A_WORKED_SHIFT))

	def test_both_states_exist_on_the_workflow(self):
		"""Every one of these is a string comparison; the wrong case filters nothing."""
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


class TestTheThreeShapesAgree(FrappeTestCase):
	"""One rule, three query shapes. Each is asked of the same four rows, and the NULL one
	is the reason all of this is written out rather than left as a bare NOT IN."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.skip = not has_workflow_state_column()

	def setUp(self):
		if self.skip:
			self.skipTest("run bench migrate - the Employee Schedule workflow is not installed")
		_clear()
		self.date = add_days(today(), 903)
		self.active = _seed("ACTIVE", ACTIVE, date=self.date)
		self.blank = _seed("BLANK", None, date=self.date)
		self.pending = _seed("PENDING", PENDING_DSOT, date=self.date)
		self.rejected = _seed("REJECTED", DSOT_REJECTED, date=self.date)

	def tearDown(self):
		_clear()

	def _kept(self):
		return {self.active, self.blank}

	def test_the_orm_filters_keep_the_right_rows(self):
		kept = set(
			frappe.get_all(
				"Employee Schedule",
				filters={"name": ["like", SEEDED + "%"], **worked_shift_filters()},
				pluck="name",
			)
		)

		self.assertEqual(kept, self._kept())

	def test_the_query_builder_criterion_keeps_the_right_rows(self):
		EmployeeSchedule = frappe.qb.DocType("Employee Schedule")
		kept = {
			row[0]
			for row in (
				frappe.qb.from_(EmployeeSchedule)
				.select(EmployeeSchedule.name)
				.where(EmployeeSchedule.name.like(SEEDED + "%"))
				.where(worked_shift_criterion(EmployeeSchedule))
			).run()
		}

		self.assertEqual(kept, self._kept())

	def test_the_sql_fragment_keeps_the_right_rows(self):
		self.assertEqual(_names_left(worked_shift_sql()), self._kept())

	def test_a_schedule_with_no_state_at_all_survives_all_three(self):
		"""The one the roster's raw INSERT creates. NULL NOT IN (...) is NULL in SQL, so
		an unguarded filter would drop every ordinary shift on the roster - which is a far
		worse failure than the one being fixed."""
		self.assertIsNone(frappe.db.get_value("Employee Schedule", self.blank, "workflow_state"))

		for shape in (
			set(frappe.get_all("Employee Schedule", filters={"name": ["like", SEEDED + "%"], **worked_shift_filters()}, pluck="name")),
			_names_left(worked_shift_sql()),
		):
			with self.subTest(shape=shape):
				self.assertIn(self.blank, shape)


class TestNoneOfItAppliesWithoutTheColumn(FrappeTestCase):
	"""A site where the Employee Schedule workflow has not been installed has no
	workflow_state column, and a filter on it would fail the whole query rather than
	narrow it. Each shape has to answer "no condition" there, not "no rows"."""

	def setUp(self):
		self._real = frappe.db.get_table_columns
		frappe.db.get_table_columns = lambda doctype: [
			column for column in self._real(doctype) if column != "workflow_state"
		]

	def tearDown(self):
		frappe.db.get_table_columns = self._real

	def test_the_orm_filters_are_empty(self):
		self.assertEqual(worked_shift_filters(), {})

	def test_there_is_no_criterion(self):
		self.assertIsNone(worked_shift_criterion(frappe.qb.DocType("Employee Schedule")))

	def test_the_sql_fragment_is_a_no_op_that_still_parses(self):
		self.assertEqual(worked_shift_sql(), "1 = 1")
		frappe.db.sql(f"SELECT name FROM `tabEmployee Schedule` WHERE {worked_shift_sql()} LIMIT 1")


class TestTheDoubleShiftOTCheckerLeavesThemAlone(FrappeTestCase):
	"""The checker that was actually raising a record against a supervisor for a shift
	nobody had approved - and for rejected ones, that nobody would ever work."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.skip = not has_workflow_state_column()
		cls.shift = frappe.db.get_value("Operations Shift", {"double_shift_ot_allowed": 0}, "name")

	def setUp(self):
		if self.skip:
			self.skipTest("run bench migrate - the Employee Schedule workflow is not installed")
		if not self.shift:
			self.skipTest("no Operations Shift with Double Shift OT disabled on this site")
		self.employees = frappe.get_all("Employee", filters={"status": "Active"}, pluck="name", limit=3)
		if len(self.employees) < 3:
			self.skipTest("needs three active employees on this site")
		_clear()
		# Inside the window the checker looks at: the current calendar week.
		self.date = today()

	def tearDown(self):
		_clear()

	def _flagged(self):
		from one_fm.operations.doctype.roster_double_shift_ot_checker.roster_double_shift_ot_checker import (
			get_disallowed_ot_schedules,
		)

		by_employee = get_disallowed_ot_schedules(add_days(self.date, -1), add_days(self.date, 1))

		return {
			(employee, schedule.date)
			for employee, schedules in by_employee.items()
			for schedule in schedules
		}

	def _seed_for(self, suffix, employee, workflow_state):
		_seed(suffix, workflow_state, employee=employee, date=self.date, shift=self.shift)
		return (employee, frappe.utils.getdate(self.date))

	def test_a_pending_double_shift_is_not_flagged(self):
		self.assertNotIn(
			self._seed_for("PENDING", self.employees[0], PENDING_DSOT), self._flagged()
		)

	def test_a_rejected_one_is_not_flagged(self):
		self.assertNotIn(
			self._seed_for("REJECTED", self.employees[1], DSOT_REJECTED), self._flagged()
		)

	def test_an_active_one_still_is(self):
		"""The other half. The checker exists to catch overtime on a shift that does not
		allow it, and a guard that silenced it altogether would be worse than the noise."""
		self.assertIn(self._seed_for("ACTIVE", self.employees[2], ACTIVE), self._flagged())


class TestTheRamboManifestLeavesThemAlone(FrappeTestCase):
	"""A reliever whose overtime is still waiting is not travelling, and a seat given to
	them is one taken from somebody who is."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.skip = not has_workflow_state_column()

	def setUp(self):
		if self.skip:
			self.skipTest("run bench migrate - the Employee Schedule workflow is not installed")

		# Flagged here rather than looked for: this site has no Rambo reliever, and a
		# skipped test is no guard at all. Rolled back with the rest of the class.
		self.reliever = frappe.db.get_value("Employee", {"status": "Active"}, "name")
		if not self.reliever:
			self.skipTest("no active employee on this site")
		self.was_reliever = frappe.db.get_value("Employee", self.reliever, "custom_is_rambo_reliever")
		frappe.db.set_value("Employee", self.reliever, "custom_is_rambo_reliever", 1, update_modified=False)

		# The compiler drops a row with no shift on it - there is nothing to attach the
		# pickup to - so a seedless-shift fixture would make every assertion here vacuous.
		self.shift = frappe.db.get_value("Operations Shift", {}, "name")
		if not self.shift:
			self.skipTest("no Operations Shift on this site")

		_clear()
		self.date = add_days(today(), 904)

	def tearDown(self):
		frappe.db.set_value(
			"Employee", self.reliever, "custom_is_rambo_reliever", self.was_reliever, update_modified=False
		)
		_clear()

	def _picked_up(self, workflow_state):
		from one_fm.one_fm.doctype.transportation_manifest.manifest_compiler import (
			_relievers_scheduled_today,
		)

		_clear()
		name = _seed("RAMBO", workflow_state, employee=self.reliever, date=self.date, shift=self.shift)
		frappe.db.set_value("Employee Schedule", name, "is_rambo_schedule", 1, update_modified=False)

		return [row.employee for row in _relievers_scheduled_today(self.date)]

	def test_a_pending_double_shift_gets_no_seat(self):
		self.assertNotIn(self.reliever, self._picked_up(PENDING_DSOT))

	def test_a_rejected_one_gets_no_seat(self):
		self.assertNotIn(self.reliever, self._picked_up(DSOT_REJECTED))

	def test_an_active_one_still_does(self):
		self.assertIn(self.reliever, self._picked_up(ACTIVE))

	def test_one_with_no_state_at_all_still_does(self):
		"""Every ordinary Basic reliever row the roster writes is this one."""
		self.assertIn(self.reliever, self._picked_up(None))


class TestTheManpowerCountLeavesThemAlone(FrappeTestCase):
	"""Contract compliance reports manpower the client was given. A double shift nobody
	has approved has put nobody on the ground."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.skip = not has_workflow_state_column()
		cls.role = frappe.db.get_value("Operations Role", {}, "name")

	def setUp(self):
		if self.skip:
			self.skipTest("run bench migrate - the Employee Schedule workflow is not installed")
		if not self.role:
			self.skipTest("no Operations Role on this site")
		_clear()
		self.date = add_days(today(), 905)

	def tearDown(self):
		_clear()

	def _counted(self, workflow_state):
		from one_fm.operations.doctype.contract_compliance_checker.contract_compliance_checker import (
			GenerateContractComplianceChecker,
		)

		_clear()
		name = _seed("MANPOWER", workflow_state, date=self.date)
		frappe.db.set_value("Employee Schedule", name, "operations_role", self.role, update_modified=False)

		checker = GenerateContractComplianceChecker.__new__(GenerateContractComplianceChecker)
		checker.yesterday = add_days(today(), -1)
		checker.day_before_yesterday = add_days(today(), -2)

		return checker.get_total_employee_schedule_count([self.role], self.date, self.date)

	def test_a_pending_double_shift_is_not_counted(self):
		self.assertEqual(self._counted(PENDING_DSOT), 0)

	def test_a_rejected_one_is_not_counted(self):
		self.assertEqual(self._counted(DSOT_REJECTED), 0)

	def test_an_active_one_is(self):
		self.assertEqual(self._counted(ACTIVE), 1)

	def test_one_with_no_state_at_all_is(self):
		self.assertEqual(self._counted(None), 1)


class TestTheMissedAssignmentEmailLeavesThemAlone(FrappeTestCase):
	"""The hourly job that emails Support a list of shifts with no Shift Assignment.

	A double shift waiting on the approver has none on purpose, and a rejected one never
	will have - so reporting either sends Support looking for a problem this system
	created deliberately. Unlike the rest of this file the job creates nothing; what it
	does is cost somebody an hour.

	Seeded and run once for the whole class: the job reads three tables of live data and
	takes the better part of a minute on this site, and the three cases are three rows in
	one answer rather than three runs of it.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.reported = None

		if not has_workflow_state_column():
			return

		cls.employees = frappe.get_all("Employee", filters={"status": "Active"}, pluck="name", limit=3)
		if len(cls.employees) < 3:
			return

		_clear()
		cls.pending = cls._due_now("HOURLY-PENDING", cls.employees[0], PENDING_DSOT)
		cls.rejected = cls._due_now("HOURLY-REJECTED", cls.employees[1], DSOT_REJECTED)
		cls.blank = cls._due_now("HOURLY-BLANK", cls.employees[2], None)
		cls.reported = cls._what_the_job_would_email()

	@classmethod
	def tearDownClass(cls):
		_clear()
		super().tearDownClass()

	def setUp(self):
		if self.reported is None:
			self.skipTest("needs the Employee Schedule workflow and three active employees")

	@staticmethod
	def _due_now(suffix, employee, workflow_state):
		"""A schedule starting at the hour the job is looking at.

		The job rounds an hour forward and compares start_datetime exactly, so the value
		is computed the same way rather than guessed.
		"""
		from datetime import datetime, timedelta

		due = datetime.strptime(
			format(datetime.now() + timedelta(hours=1), "%d-%m-%Y %H:00:00"), "%d-%m-%Y %H:00:00"
		)
		name = _seed(suffix, workflow_state, employee=employee, date=due.date())
		frappe.db.set_value("Employee Schedule", name, "start_datetime", due, update_modified=False)
		return name

	@staticmethod
	def _what_the_job_would_email():
		"""Caught at the email rather than read off the query - the job builds its list
		from three sources and only one of them is the one under test."""
		import one_fm.api.tasks as tasks

		captured = {}
		original = tasks.missing_shift_assignment_support_email
		tasks.missing_shift_assignment_support_email = (
			lambda roster, *args, **kwargs: captured.setdefault("roster", roster)
		)
		try:
			tasks.validate_shift_assignment(is_scheduled_event=False)
		finally:
			tasks.missing_shift_assignment_support_email = original

		return {row.get("name") for row in (captured.get("roster") or [])}

	def test_a_pending_double_shift_is_not_reported(self):
		self.assertNotIn(self.pending, self.reported)

	def test_a_rejected_one_is_not_reported(self):
		self.assertNotIn(self.rejected, self.reported)

	def test_a_shift_with_no_assignment_and_no_state_still_is(self):
		"""The other half, and the one that matters most: this job's whole purpose is to
		notice a missing Shift Assignment, and an over-broad guard would silence it."""
		self.assertIn(self.blank, self.reported)


class TestThePostActionsJobCarriesTheFilter(FrappeTestCase):
	"""The daily job that decides which operations roles are unfilled or over-filled.

	Its Employee Schedule query is raw SQL behind four joins and an EXISTS against live
	Contracts, so a fixture that reaches it would be most of a contract. The query is
	caught on its way to the database instead, which is what actually has to carry the
	filter - an f-string that lost it would otherwise still run, and still count a double
	shift nobody has approved as a filled post.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.skip = not has_workflow_state_column()

	def setUp(self):
		if self.skip:
			self.skipTest("run bench migrate - the Employee Schedule workflow is not installed")

	def test_the_query_it_runs_excludes_them(self):
		from one_fm.one_fm.doctype.roster_post_actions import roster_post_actions

		class Caught(Exception):
			pass

		seen = []
		original = frappe.db.sql

		def spy(query, *args, **kwargs):
			text = str(query)
			if "tabEmployee Schedule" in text:
				seen.append(text)
				# Nothing past this point is under test, and the rest of the job writes
				# documents.
				raise Caught
			if "tabPost Schedule" in text:
				# Answered without touching the database: it reads a month of live post
				# schedules across four joins, and the job runs it twice before it ever
				# reaches the query under test.
				return []
			return original(query, *args, **kwargs)

		frappe.db.sql = spy
		try:
			roster_post_actions.create_roster_post_actions()
		except Caught:
			pass
		finally:
			frappe.db.sql = original

		self.assertTrue(seen, "the job never queried Employee Schedule")
		self.assertIn(worked_shift_sql(), seen[0])
