# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Task Type holds only Action, Process, Project and Routine.

Two halves are covered: the helper that hands out a task type, and the patch
that clears the retired records out of an existing site.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0.reduce_task_type_to_four_records import (
	RETIRED_TASK_TYPES,
	execute as reduce_task_types,
)
from one_fm.utils import ALLOWED_TASK_TYPES, get_task_type


class TestGetTaskType(FrappeTestCase):
	def test_allowed_set_is_exactly_the_four(self):
		self.assertEqual(ALLOWED_TASK_TYPES, {"Action", "Process", "Project", "Routine"})

	def test_the_default_is_an_allowed_type(self):
		self.assertIn(get_task_type(), ALLOWED_TASK_TYPES)

	def test_a_retired_name_is_remapped(self):
		for retired in RETIRED_TASK_TYPES:
			with self.subTest(retired=retired):
				self.assertEqual(get_task_type(retired), "Project")

	def test_an_allowed_type_is_returned_unchanged(self):
		for allowed in ALLOWED_TASK_TYPES:
			with self.subTest(allowed=allowed):
				self.assertEqual(get_task_type(allowed), allowed)

	def test_an_unknown_name_falls_back_to_project(self):
		self.assertEqual(get_task_type("Some Name Nobody Has Used"), "Project")
		self.assertFalse(frappe.db.exists("Task Type", "Some Name Nobody Has Used"))


class TestReduceTaskTypesPatch(FrappeTestCase):
	def setUp(self):
		for retired in RETIRED_TASK_TYPES:
			if not frappe.db.exists("Task Type", retired):
				frappe.get_doc({
					"doctype": "Task Type", "name": retired, "is_routine_task": 0
				}).insert()
		if not frappe.db.exists("Task Type", "Routine"):
			frappe.get_doc({
				"doctype": "Task Type", "name": "Routine", "is_routine_task": 1
			}).insert()

		self.retired_task = frappe.get_doc({
			"doctype": "Task", "subject": "Retired type", "type": "Repetitive",
		}).insert()
		self.routine_task = frappe.get_doc({
			"doctype": "Task", "subject": "Routine type", "type": "Routine",
		}).insert()

	def test_only_the_four_survive(self):
		reduce_task_types()

		surviving = frappe.get_all("Task Type", pluck="name")
		for kept in ALLOWED_TASK_TYPES:
			self.assertIn(kept, surviving)
		for retired in RETIRED_TASK_TYPES:
			self.assertNotIn(retired, surviving)

	def test_a_retired_task_moves_to_project_and_a_routine_one_does_not_move(self):
		reduce_task_types()

		self.assertEqual(frappe.db.get_value("Task", self.retired_task.name, "type"), "Project")
		self.assertEqual(frappe.db.get_value("Task", self.routine_task.name, "type"), "Routine")

	def test_running_it_twice_changes_nothing(self):
		reduce_task_types()
		before = sorted(frappe.get_all("Task Type", pluck="name"))

		reduce_task_types()

		self.assertEqual(sorted(frappe.get_all("Task Type", pluck="name")), before)
		self.assertEqual(frappe.db.get_value("Task", self.routine_task.name, "type"), "Routine")
