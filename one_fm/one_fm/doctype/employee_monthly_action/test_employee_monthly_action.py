# Copyright (c) 2025, ONE FM and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today


class TestEmployeeMonthlyAction(FrappeTestCase):
	@patch("one_bpmn.one_bpmn.trigger.on_doc_event")
	def test_submitting_leaves_goal_progress_to_the_process_map(self, _trigger):
		employee = frappe.get_all(
			"Employee", filters={"status": "Active", "user_id": ["is", "set"]}, fields=["name", "company"], limit=1
		)[0]
		goal = frappe.get_doc({
			"doctype": "Goal",
			"goal_name": "progress probe",
			"employee": employee.name,
			"start_date": today(),
			"end_date": today(),
			"progress": 10,
			"status": "In Progress",
		}).insert()
		# The old controller looked the Goal up by its title, so the title must equal the id for that path to be reachable.
		goal.db_set("goal_name", goal.name)

		action = frappe.get_doc({
			"doctype": "Employee Monthly Action",
			"employee": employee.name,
			"company": employee.company,
			"month": "January",
			"year": frappe.get_all("Fiscal Year", limit=1, pluck="name")[0],
			"goal_update": [{"goal": goal.name, "previous_progress": 10, "current_progress": 80}],
		}).insert()
		action.run_method("on_submit")

		self.assertEqual(frappe.db.get_value("Goal", goal.name, "progress"), 10)
