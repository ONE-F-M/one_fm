# Copyright (c) 2025, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_random_string

from one_fm.one_fm.doctype.leave_handover.leave_handover import get_handover_data


class TestLeaveHandover(FrappeTestCase):
	def setUp(self):
		# Create roles if they don't exist
		for role in ["Project Access", "Project Update"]:
			if not frappe.db.exists("Role", role):
				frappe.get_doc({"doctype": "Role", "role_name": role}).insert()

		# Create users
		self.user_on_leave = self.create_user("test_user_on_leave@example.com")
		self.reliever_user = self.create_user("test_reliever_user@example.com")

		# Create employees
		self.employee_on_leave = self.create_employee(self.user_on_leave.name)
		self.reliever_employee = self.create_employee(self.reliever_user.name)

		# Create a project
		self.project = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": "Test Handover Project " + get_random_string(5),
				"account_manager": self.employee_on_leave.name,
				"status": "Open",
			}
		).insert()

		# Create a leave application
		self.leave_application = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": self.employee_on_leave.name,
				"from_date": "2025-10-21",
				"to_date": "2025-10-22",
				"leave_type": "Privilege Leave",
				"status": "Approved",
			}
		).insert()
		self.leave_application.submit()

	def tearDown(self):
		# Clean up created documents
		frappe.db.rollback()

	def create_user(self, email):
		if frappe.db.exists("User", email):
			return frappe.get_doc("User", email)
		return frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
		).insert()

	def create_employee(self, user_id):
		employee_name = user_id.split("@")[0]
		if frappe.db.exists("Employee", {"user_id": user_id}):
			return frappe.get_doc("Employee", {"user_id": user_id})

		# Ensure _Test Company exists
		if not frappe.db.exists("Company", "_Test Company"):
			frappe.get_doc({"doctype": "Company", "company_name": "_Test Company", "default_currency": "USD"}).insert()

		if not frappe.db.exists("Leave Type", "Privilege Leave"):
			frappe.get_doc({"doctype": "Leave Type", "leave_type_name": "Privilege Leave", "max_days_allowed": 30}).insert()

		return frappe.get_doc(
			{
				"doctype": "Employee",
				"employee_name": employee_name.replace("_", " ").title(),
				"company": "_Test Company",
				"user_id": user_id,
				"status": "Active",
			}
		).insert()

	def test_role_assignment_on_submit(self):
		# Create Leave Handover
		leave_handover = frappe.get_doc(get_handover_data(self.leave_application.name))
		leave_handover.insert()

		# Update handover item with reliever and status
		item = leave_handover.handover_items[0]
		item.reliever = self.reliever_employee.name
		item.status = "Accepted"
		leave_handover.save()

		# Submit the document
		frappe.set_user(self.user_on_leave.name)  # set user to employee on leave to submit
		leave_handover.submit()
		frappe.set_user("Administrator")  # revert back to admin

		# Assertions
		# 1. Check if reliever user has the roles
		reliever_user_doc = frappe.get_doc("User", self.reliever_user.name)
		reliever_roles = [d.role for d in reliever_user_doc.roles]
		self.assertIn("Project Access", reliever_roles)
		self.assertIn("Project Update", reliever_roles)

		# 2. Check if the roles_assigned field is updated
		updated_handover = frappe.get_doc("Leave Handover", leave_handover.name)
		self.assertEqual(
			updated_handover.handover_items[0].roles_assigned, "Project Access, Project Update"
		)
