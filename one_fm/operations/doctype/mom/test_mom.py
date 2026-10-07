# -*- coding: utf-8 -*-
# Copyright (c) 2020, ONE FM and Contributors
# See license.txt
from __future__ import unicode_literals

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today, add_days

class TestMOM(FrappeTestCase):
	def setUp(self):
		# Clean up any existing test project/MOM records to prevent duplicate key errors
		if frappe.db.exists("Project", "Test MOM Sync Project"):
			frappe.delete_doc("Project", "Test MOM Sync Project", force=True, ignore_missing=True)
		
		# Create a test project
		self.project = frappe.new_doc("Project")
		self.project.project_name = "Test MOM Sync Project"
		self.project.project_type = "Internal"
		self.project.insert()

	def tearDown(self):
		# Clean up after each test
		frappe.db.rollback()

	def test_saving_leaves_task_creation_to_the_process_map(self):
		mom = frappe.new_doc("MOM")
		mom.project = self.project.name
		mom.project_type = "Internal"
		mom.append("general_attendance", {"attendee_name": "Test Attendee", "attended_meeting": 1})
		mom.append("action", {"subject": "Action Task 1", "description": "Test description", "priority": "High"})
		mom.append("pending_actions", {"subject": "Pending Task", "priority": "Medium", "status": "Open", "due_date": today()})
		mom.insert()

		self.assertEqual(frappe.db.count("Task", {"custom_mom": mom.name}), 0)
		self.assertIsNone(mom.pending_actions[0].task)

	def test_review_last_actions_and_fallback(self):
		# Create first MOM
		mom1 = frappe.new_doc("MOM")
		mom1.project = self.project.name
		mom1.project_type = "Internal"
		mom1.append("general_attendance", {
			"attendee_name": "Test Attendee",
			"attended_meeting": 1
		})
		mom1.append("action", {
			"subject": "Action from MOM 1",
			"description": "MOM 1 action description",
			"priority": "Low"
		})
		mom1.insert()
		task = frappe.new_doc("Task")
		task.project = self.project.name
		task.subject = "Action from MOM 1"
		task.custom_mom = mom1.name
		task.insert()

		# Check that we can fetch the task via review_last_actions
		from one_fm.operations.doctype.mom.mom import review_last_actions
		data = review_last_actions(last_mom_name=mom1.name, project=self.project.name)
		self.assertEqual(len(data), 1)
		self.assertEqual(data[0]["subject"], "Action from MOM 1")

	def test_update_task_from_mom_api(self):
		# Create a task
		task = frappe.new_doc("Task")
		task.project = self.project.name
		task.subject = "API Sync Task"
		task.status = "Open"
		task.insert()

		from one_fm.operations.doctype.mom.mom import update_task_from_mom
		update_task_from_mom(
			task_name=task.name,
			subject="API Sync Task Updated",
			status="Working",
			priority="High",
			due_date=add_days(today(), 5)
		)

		# Verify task was updated
		updated_task = frappe.get_doc("Task", task.name)
		self.assertEqual(updated_task.subject, "API Sync Task Updated")
		self.assertEqual(updated_task.status, "Working")
		self.assertEqual(updated_task.priority, "High")
		self.assertEqual(str(updated_task.exp_end_date), str(add_days(today(), 5)))
