# Copyright (c) 2025, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from one_fm.patches.v15_0.remove_daily_employee_action_check import METHOD, execute


class TestRemoveDailyEmployeeActionCheck(FrappeTestCase):
	def test_patch_removes_the_scheduling_records(self):
		if not frappe.db.exists("Method", METHOD):
			frappe.get_doc(
				{"doctype": "Method", "method": METHOD, "document_type": "Employee Daily Action", "description": "probe"}
			).insert()
		if not frappe.db.exists("Scheduled Job Type", {"method": METHOD}):
			frappe.get_doc(
				{"doctype": "Scheduled Job Type", "method": METHOD, "frequency": "Cron", "cron_format": "0 4 * * *"}
			).insert()

		execute()

		self.assertFalse(frappe.db.exists("Scheduled Job Type", {"method": METHOD}))
		self.assertFalse(frappe.db.exists("Process Task", {"method": METHOD}))
		self.assertFalse(frappe.db.exists("Method", METHOD))


class TestEmployeeDailyActionController(FrappeTestCase):
	def test_saving_leaves_plans_and_reports_to_to_the_process_map(self):
		employee = frappe.get_all(
			"Employee", filters={"status": "Active", "user_id": ["is", "set"]}, fields=["name", "user_id", "company"], limit=1
		)[0]
		frappe.get_doc({"doctype": "ToDo", "allocated_to": employee.user_id, "date": today(), "description": "plan probe"}).insert()

		eda = frappe.get_doc({
			"doctype": "Employee Daily Action",
			"company_name": employee.company,
			"employee": employee.name,
			"date": today(),
			"number_of_read_emails": "0",
			"number_of_unread_emails": "0",
			"number_of_open_drive_comments": "0",
		}).insert()

		self.assertEqual(eda.todays_plan_and_accomplishments, [])
