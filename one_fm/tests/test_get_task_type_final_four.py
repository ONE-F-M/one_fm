# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-002959: Task Type is reduced to exactly Action, Process, Project and Routine.

get_task_type() (one_fm/one_fm/utils.py) used to default to, and silently create,
"Repetitive" - one of the four types this work order deletes. If that behaviour ever
comes back, the deleted Task Type is recreated on the next call and the whole point of
the migration patch is undone. These tests pin get_task_type() to the final four so a
revert of that change is caught here rather than in production data again.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.utils import ALLOWED_TASK_TYPES, get_task_type

DELETED_TASK_TYPES = ["Active Repetitive", "develop", "Individual", "Repetitive"]


class TestGetTaskTypeCannotCreateOutsideTheFinalFour(FrappeTestCase):
	def test_allowed_set_is_exactly_the_final_four(self):
		self.assertEqual(ALLOWED_TASK_TYPES, {"Action", "Process", "Project", "Routine"})

	def test_default_call_does_not_create_a_deleted_type(self):
		"""Calling get_task_type() with no arguments used to default to, and insert,
		"Repetitive". It must not be able to do that again."""
		result = get_task_type()

		self.assertIn(result, ALLOWED_TASK_TYPES)
		self.assertNotEqual(result, "Repetitive")

	def test_a_deleted_type_name_is_never_created(self):
		"""Even if some caller still passes one of the deleted names explicitly, it must
		be remapped rather than recreated."""
		for deleted_type in DELETED_TASK_TYPES:
			with self.subTest(deleted_type=deleted_type):
				result = get_task_type(deleted_type)

				self.assertIn(result, ALLOWED_TASK_TYPES)
				self.assertNotEqual(result, deleted_type)
				self.assertFalse(frappe.db.exists("Task Type", deleted_type))

	def test_an_allowed_type_is_returned_unchanged(self):
		for allowed_type in ALLOWED_TASK_TYPES:
			with self.subTest(allowed_type=allowed_type):
				self.assertEqual(get_task_type(allowed_type), allowed_type)

	def test_an_unknown_type_is_remapped_to_project_not_inserted(self):
		"""A completely new/unexpected name must fall back to "Project" rather than be
		created verbatim - the four-type constraint has to hold for any input, not just
		the five names known about today."""
		result = get_task_type("Some Brand New Type WI-002959")

		self.assertEqual(result, "Project")
		self.assertFalse(frappe.db.exists("Task Type", "Some Brand New Type WI-002959"))
