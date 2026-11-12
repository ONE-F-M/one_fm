# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.legal.doctype.hr_enquiry.hr_enquiry import get_permission_query_conditions, has_permission

EMPLOYEE_USER = "hr-enquiry-employee@example.com"
HR_USER = "hr-enquiry-hr@example.com"


def make_user(email: str, roles: list) -> str:
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	user = frappe.get_doc("User", email)
	user.add_roles(*roles)
	return email


class TestHREnquiry(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		make_user(EMPLOYEE_USER, ["Employee"])
		make_user(HR_USER, ["HR User"])

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_hr_investigator_defaults_from_legal_settings(self):
		frappe.db.set_single_value("Legal Settings", "hr_investigator", HR_USER)
		enquiry = frappe.get_doc({"doctype": "HR Enquiry"})
		enquiry.run_method("before_insert")
		self.assertEqual(enquiry.hr_investigator, HR_USER)

	def test_an_explicit_hr_investigator_is_kept(self):
		frappe.db.set_single_value("Legal Settings", "hr_investigator", HR_USER)
		enquiry = frappe.get_doc({"doctype": "HR Enquiry", "hr_investigator": "Administrator"})
		enquiry.run_method("before_insert")
		self.assertEqual(enquiry.hr_investigator, "Administrator")

	def test_reviewers_see_every_enquiry(self):
		self.assertEqual(get_permission_query_conditions(HR_USER), "")
		self.assertTrue(has_permission(frappe._dict(employee_user="someone@example.com"), "read", HR_USER))

	def test_an_employee_sees_only_their_own_enquiry(self):
		self.assertIn(EMPLOYEE_USER, get_permission_query_conditions(EMPLOYEE_USER))
		self.assertTrue(has_permission(frappe._dict(employee_user=EMPLOYEE_USER), "read", EMPLOYEE_USER))
		self.assertFalse(
			has_permission(frappe._dict(employee_user="someone@example.com"), "read", EMPLOYEE_USER)
		)

	def test_only_hr_records_the_decision(self):
		enquiry = frappe.get_doc({"doctype": "HR Enquiry", "hr_decision": "Overturn Penalty"})
		frappe.set_user(EMPLOYEE_USER)
		self.assertRaises(frappe.PermissionError, enquiry.validate_decision_maker)

		frappe.set_user(HR_USER)
		enquiry.validate_decision_maker()

	def test_the_lifecycle_states_exist_with_a_style(self):
		from one_fm.patches.v15_0.create_hr_enquiry_workflow_states import STATES, execute

		execute()
		for state, style in STATES:
			self.assertEqual(frappe.db.get_value("Workflow State", state, "style"), style)
