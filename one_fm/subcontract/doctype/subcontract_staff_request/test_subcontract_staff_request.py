# Copyright (c) 2023, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.custom.custom_field.project import get_project_custom_fields


class TestSubcontractStaffRequest(FrappeTestCase):
	def test_project_manager_user_fetches_from_project(self):
		field = frappe.get_meta("Subcontract Staff Request").get_field("project_manager_user")
		self.assertEqual(field.fetch_from, "project.custom_project_manager_user")
		self.assertTrue(field.read_only)

	def test_project_defines_project_manager_user(self):
		fields = {f["fieldname"]: f for f in get_project_custom_fields()["Project"]}
		self.assertEqual(fields["custom_project_manager_user"]["fetch_from"], "project_manager.user_id")
		self.assertTrue(frappe.get_meta("Project").has_field("custom_project_manager_user"))
