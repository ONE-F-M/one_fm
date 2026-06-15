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

	def test_task_creation_on_submit(self):
		# Create a draft MOM
		mom = frappe.new_doc("MOM")
		mom.project = self.project.name
		mom.project_type = "Internal"
		mom.append("general_attendance", {
			"attendee_name": "Test Attendee",
			"attended_meeting": 1
		})
		mom.append("action", {
			"subject": "Action Task 1",
			"description": "Test description",
			"priority": "High"
		})
		mom.insert()
		mom.submit()

		# Check if task was created and linked to MOM via custom_mom
		tasks = frappe.get_all("Task", filters={"custom_mom": mom.name}, fields=["name", "subject", "description"])
		self.assertEqual(len(tasks), 1)
		self.assertEqual(tasks[0].subject, "Action Task 1")

	def test_sync_tasks_from_tables_on_save(self):
		# Create a draft MOM
		mom = frappe.new_doc("MOM")
		mom.project = self.project.name
		mom.project_type = "Internal"
		mom.issues = "No"
		mom.append("general_attendance", {
			"attendee_name": "Test Attendee",
			"attended_meeting": 1
		})
		
		# Add a row to pending_actions table without an existing task link
		mom.append("pending_actions", {
			"subject": "Draft Sync Task",
			"description": "Needs to be created on save",
			"priority": "Medium",
			"status": "Open",
			"due_date": today()
		})
		mom.insert()

		# On insert/save, validate() should have automatically created the Task and linked it
		self.assertIsNotNone(mom.pending_actions[0].task)
		task_name = mom.pending_actions[0].task

		task = frappe.get_doc("Task", task_name)
		self.assertEqual(task.subject, "Draft Sync Task")
		self.assertEqual(task.status, "Open")
		self.assertEqual(task.custom_mom, mom.name)

		# Modify the row in the child table and save again
		mom.pending_actions[0].status = "Working"
		mom.pending_actions[0].priority = "High"
		mom.save()

		# Verify task was updated
		task = frappe.get_doc("Task", task_name)
		self.assertEqual(task.status, "Working")
		self.assertEqual(task.priority, "High")

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
		mom1.submit()

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
