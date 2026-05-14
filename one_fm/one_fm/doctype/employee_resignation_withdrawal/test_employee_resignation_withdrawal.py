# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

class TestEmployeeResignationWithdrawal(FrappeTestCase):
	def setUp(self):
		emp_name = _make_employee("test_erw_employee@example.com", "Test ERW Employee")
		self.employee = frappe.get_doc("Employee", emp_name)
		
		# Create an Employee Resignation
		self.resignation = frappe.get_doc({
			"doctype": "Employee Resignation",
			"employee": self.employee.name,
			"resignation_letter_date": frappe.utils.today(),
			"reason_for_resignation": "Better opportunity",
			"resignation_letter": "/files/resignation_letter.txt",
			"status": "Pending",
			"relieving_date": frappe.utils.add_days(frappe.utils.today(), 30)
		}).insert(ignore_permissions=True)
		
	def tearDown(self):
		frappe.db.rollback()

	def test_validate_rejection_reason_missing(self):
		erw = frappe.get_doc({
			"doctype": "Employee Resignation Withdrawal",
			"employee_resignation": self.resignation.name,
			"reason": "Test",
			"resignation_withdrawal_letter": "/files/test.txt",
			"workflow_state": "Pending Supervisor"
		}).insert(ignore_permissions=True)

		# Change state without giving reason
		erw.workflow_state = "Rejected By Supervisor"
		
		with self.assertRaises(frappe.ValidationError) as context:
			erw.save(ignore_permissions=True)
		
		self.assertTrue("Please provide Reason for Rejection" in str(context.exception))

	def test_validate_rejection_reason_provided(self):
		erw = frappe.get_doc({
			"doctype": "Employee Resignation Withdrawal",
			"employee_resignation": self.resignation.name,
			"reason": "Test",
			"resignation_withdrawal_letter": "/files/test.txt",
			"workflow_state": "Pending Supervisor"
		}).insert(ignore_permissions=True)

		# Change state and provide reason
		erw.workflow_state = "Rejected By Supervisor"
		erw.reason_for_rejection = "Not a valid reason"
		
		# Should not raise any error
		erw.save(ignore_permissions=True)
		self.assertEqual(erw.workflow_state, "Rejected By Supervisor")

	def test_process_withdrawal_approval(self):
		# Create a PMR tied to the resignation if the doctype exists
		pmr = None
		if frappe.db.exists("DocType", "Project Manpower Request"):
			pmr = frappe.get_doc({
				"doctype": "Project Manpower Request",
				"employee_resignation": self.resignation.name,
				"project": _get_or_create_project(),
				"title": "Test PMR"
			}).insert(ignore_permissions=True)

		# Set an initial relieving date on the employee to verify it gets cleared
		frappe.db.set_value("Employee", self.employee.name, "relieving_date", frappe.utils.today())

		erw = frappe.get_doc({
			"doctype": "Employee Resignation Withdrawal",
			"employee_resignation": self.resignation.name,
			"reason": "Changed my mind",
			"resignation_withdrawal_letter": "/files/test.txt",
			"workflow_state": "Pending Supervisor"
		}).insert(ignore_permissions=True)

		# Transition 1
		erw.workflow_state = "Accepted by Supervisor"
		erw.save(ignore_permissions=True)

		# Trigger withdrawal approval
		erw.workflow_state = "Approved"
		erw.save(ignore_permissions=True)

		# Assertions
		self.employee.reload()
		self.resignation.reload()

		self.assertEqual(self.resignation.status, "Withdrawn")
		if frappe.db.has_column("Employee Resignation", "workflow_state"):
			self.assertEqual(self.resignation.workflow_state, "Withdrawn")
		
		self.assertIsNone(self.employee.relieving_date)
		
		if pmr:
			pmr.reload()
			self.assertEqual(pmr.status, "Withdrawn")
			if frappe.db.has_column("Project Manpower Request", "workflow_state"):
				self.assertEqual(pmr.workflow_state, "Withdrawn")

	def test_withdrawal_blocked_when_pmr_completed(self):
		if frappe.db.exists("DocType", "Project Manpower Request"):
			pmr = frappe.get_doc({
				"doctype": "Project Manpower Request",
				"employee_resignation": self.resignation.name,
				"project": _get_or_create_project(),
				"title": "Test PMR",
				"workflow_state": "Completed"
			}).insert(ignore_permissions=True)
			
			erw = frappe.get_doc({
				"doctype": "Employee Resignation Withdrawal",
				"employee_resignation": self.resignation.name,
				"reason": "Changed my mind",
				"resignation_withdrawal_letter": "/files/test.txt",
			})
			
			with self.assertRaises(frappe.ValidationError) as context:
				erw.validate()
			
			self.assertTrue("Cannot withdraw resignation because the replacement Project Manpower Request" in str(context.exception))

def _get_or_create_project():
	project_name = "Test Project"
	if not frappe.db.exists("Project", project_name):
		frappe.get_doc({
			"doctype": "Project",
			"project_name": project_name
		}).insert(ignore_permissions=True)
	return project_name

def _make_employee(employee_id, employee_name):
	company = frappe.db.get_single_value("Global Defaults", "default_company") or frappe.get_all("Company", limit=1)[0].name
	existing = frappe.db.get_value("Employee", {"employee": employee_id})
	if not existing:
		doc = frappe.get_doc({
			"doctype": "Employee",
			"employee": employee_id,
			"employee_name": employee_name,
			"first_name": employee_name,
			"last_name": "Test",
			"one_fm_first_name_in_arabic": "تست",
			"one_fm_last_name_in_arabic": "تست",
			"gender": "Male",
			"date_of_birth": "1990-01-01",
			"company": company,
			"department": _get_or_create_department("Test Department", company),
			"one_fm_basic_salary": 1000,
			"date_of_joining": frappe.utils.add_days(frappe.utils.today(), -100),
			"status": "Active"
		}).insert(ignore_permissions=True)
		return doc.name
	return existing

def _get_or_create_department(department_name, company):
	# The actual name in DB is usually 'Department Name - Company Abbr'
	# To make it simple, let's just create a unique one or get it if exists
	company_abbr = frappe.get_cached_value('Company', company, 'abbr') or company
	full_dept_name = f"{department_name} - {company_abbr}"
	
	if not frappe.db.exists("Department", full_dept_name):
		frappe.get_doc({
			"doctype": "Department",
			"department_name": department_name,
			"department_code": "TEST-DEPT",
			"company": company
		}).insert(ignore_permissions=True)
	return full_dept_name
