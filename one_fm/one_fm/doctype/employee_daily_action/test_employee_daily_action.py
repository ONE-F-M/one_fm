# Copyright (c) 2025, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0.remove_daily_employee_action_check import METHOD, execute


class TestRemoveDailyEmployeeActionCheck(FrappeTestCase):
	def test_patch_removes_the_scheduling_records(self):
		if not frappe.db.exists("Method", METHOD):
			frappe.get_doc(
				{"doctype": "Method", "method": METHOD, "document_type": "Employee Daily Action"}
			).insert()
		if not frappe.db.exists("Scheduled Job Type", {"method": METHOD}):
			frappe.get_doc(
				{"doctype": "Scheduled Job Type", "method": METHOD, "frequency": "Cron", "cron_format": "0 4 * * *"}
			).insert()

		execute()

		self.assertFalse(frappe.db.exists("Scheduled Job Type", {"method": METHOD}))
		self.assertFalse(frappe.db.exists("Process Task", {"method": METHOD}))
		self.assertFalse(frappe.db.exists("Method", METHOD))
