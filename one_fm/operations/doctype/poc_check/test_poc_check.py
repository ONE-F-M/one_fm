# Copyright (c) 2024, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestPOCCheck(FrappeTestCase):
	def test_saving_leaves_the_operations_manager_to_the_process_map(self):
		frappe.db.set_single_value("Operation Settings", "default_operation_manager", "Administrator")

		poc_check = frappe.get_doc({"doctype": "POC Check", "supervisor_name": "probe"}).insert()

		self.assertFalse(poc_check.operations_manager_user)
