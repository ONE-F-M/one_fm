# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestProjectManpowerRequest(FrappeTestCase):
	def setUp(self):
		self.test_email = f"test_recruiter_{frappe.generate_hash(length=8)}@example.com"
		self.recruiter = _make_user(self.test_email, "Recruiter")
		
		self.pmr = frappe.get_doc({
			"doctype": "Project Manpower Request",
			"title": "Test PMR Recruitment",
			"reason": "New Position",
			"count": 1,
			"recruiter": self.recruiter
		})
		self.pmr.flags.ignore_mandatory = True
		self.pmr.insert(ignore_permissions=True)

	def tearDown(self):
		frappe.db.rollback()

	def test_assign_recruiter_creates_todo_only_once(self):
		# Initially assigned
		self.pmr.assign_recruiter()
		
		todos = frappe.get_all("ToDo", {
			"reference_type": "Project Manpower Request",
			"reference_name": self.pmr.name,
			"allocated_to": self.recruiter,
			"status": "Open"
		})
		
		self.assertEqual(len(todos), 1)
		
		# Second assignment attempt should not create a duplicate
		self.pmr.assign_recruiter()
		
		todos_after = frappe.get_all("ToDo", {
			"reference_type": "Project Manpower Request",
			"reference_name": self.pmr.name,
			"allocated_to": self.recruiter,
			"status": "Open"
		})
		
		self.assertEqual(len(todos_after), 1)

def _make_user(email, first_name="Test"):
	if frappe.db.exists("User", email):
		return email
	user = frappe.get_doc({
		"doctype": "User",
		"email": email,
		"first_name": first_name,
		"send_welcome_email": 0
	})
	user.insert(ignore_permissions=True)
	return user.name
