# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""The patch gives Recruiter read and write on BPMN Process Instance without taking access from other roles."""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.patches.v15_0.add_recruiter_bpmn_process_instance_permission import DOCTYPE, ROLE, execute

STANDARD_ROLES = ("System Manager", "Process Owner", "Employee")


def _custom_rows():
	return {
		row.role: row
		for row in frappe.get_all(
			"Custom DocPerm",
			filters={"parent": DOCTYPE, "permlevel": 0, "if_owner": 0},
			fields=["role", "read", "write", "create"],
		)
	}


class TestAddRecruiterBpmnProcessInstancePermission(FrappeTestCase):
	def setUp(self):
		if not frappe.db.exists("DocType", DOCTYPE):
			self.skipTest("one_bpmn is not installed")
		frappe.db.delete("Custom DocPerm", {"parent": DOCTYPE})
		frappe.clear_cache(doctype=DOCTYPE)

	def tearDown(self):
		frappe.db.rollback()
		frappe.clear_cache(doctype=DOCTYPE)

	def test_recruiter_gets_read_and_write(self):
		execute()

		recruiter = _custom_rows()[ROLE]
		self.assertEqual((recruiter.read, recruiter.write, recruiter.create), (1, 1, 0))

	def test_standard_roles_keep_their_access(self):
		execute()

		rows = _custom_rows()
		for role in STANDARD_ROLES:
			self.assertEqual((rows[role].read, rows[role].write), (1, 1), role)

	def test_running_twice_adds_no_second_row(self):
		execute()
		execute()

		self.assertEqual(frappe.db.count("Custom DocPerm", {"parent": DOCTYPE, "role": ROLE}), 1)

	def test_recruiter_without_employee_role_can_write_an_instance(self):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": "bpmn-recruiter-perm@example.com",
				"first_name": "Recruiter",
				"send_welcome_email": 0,
				"roles": [{"role": ROLE}],
			}
		).insert()
		self.assertFalse(frappe.has_permission(DOCTYPE, "write", user=user.name))

		execute()

		frappe.clear_cache(user=user.name)
		self.assertTrue(frappe.has_permission(DOCTYPE, "write", user=user.name))
