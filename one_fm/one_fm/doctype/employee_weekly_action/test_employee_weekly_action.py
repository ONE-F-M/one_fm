# Copyright (c) 2025, ONE FM and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


class TestEmployeeWeeklyAction(FrappeTestCase):
	@patch("one_bpmn.one_bpmn.trigger.on_doc_event")
	def test_submitting_leaves_the_blockers_to_the_process_map(self, _trigger):
		employee = frappe.get_all(
			"Employee", filters={"status": "Active", "user_id": ["is", "set"]}, fields=["name", "company"], limit=1
		)[0]
		action = frappe.get_doc({
			"doctype": "Employee Weekly Action",
			"employee": employee.name,
			"company": employee.company,
			"week": 1,
			"year": frappe.get_all("Fiscal Year", limit=1, pluck="name")[0],
			"blockers": [{"problem": "blocker probe", "priority": "High"}],
		}).insert()
		action.run_method("on_submit")

		self.assertEqual(frappe.db.count("Blocker", {"reference_name": action.name}), 0)
