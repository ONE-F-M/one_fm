# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""The patch creates the role that gates the mobile app's crash-reporting checks."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0 import create_mobile_app_tester_role

ROLE = "Mobile App Tester"


class TestMobileAppTesterRole(FrappeTestCase):
	def test_creates_the_role_without_desk_access(self):
		frappe.delete_doc("Role", ROLE, force=True, ignore_missing=True)
		create_mobile_app_tester_role.execute()
		self.assertEqual(frappe.db.get_value("Role", ROLE, "desk_access"), 0)

	def test_running_twice_keeps_one_role(self):
		create_mobile_app_tester_role.execute()
		create_mobile_app_tester_role.execute()
		self.assertEqual(frappe.db.count("Role", {"name": ROLE}), 1)
