# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate


class TestEmployeeResignationDateAdjustment(FrappeTestCase):
	def setUp(self):
		emp_name = _make_employee("test_erda_employee@example.com", "Test ERDA Employee")
		self.employee = frappe.get_doc("Employee", emp_name)

		self.relieving_date = frappe.utils.add_days(frappe.utils.today(), 30)
		self.extended_relieving_date = frappe.utils.add_days(frappe.utils.today(), 45)

		self.resignation = frappe.get_doc({
			"doctype": "Employee Resignation",
			"employee": self.employee.name,
			"resignation_initiation_date": frappe.utils.today(),
			"reason_for_exit": "Better opportunity",
			"resignation_letter": "/files/resignation_letter.txt",
			"relieving_date": self.relieving_date,
		}).insert()

		self.pmr = frappe.get_doc({
			"doctype": "Project Manpower Request",
			"employee_resignation": self.resignation.name,
			"project_allocation": self.employee.project,
			"deployment_date": frappe.utils.add_days(self.relieving_date, -11),
			"ojt_days": 11,
			"title": "Test ERDA PMR",
		})
		self.pmr.flags.ignore_mandatory = True
		self.pmr.insert()

	def tearDown(self):
		frappe.db.rollback()

	def test_draft_allows_missing_extended_relieving_date(self):
		ext = frappe.get_doc({
			"doctype": "Employee Resignation Date Adjustment",
			"employee_resignation": self.resignation.name,
		}).insert()

		self.assertEqual(ext.workflow_state, "Draft")
		self.assertIsNone(ext.extended_relieving_date)

	def test_submit_for_review_requires_extended_relieving_date(self):
		ext = frappe.get_doc({
			"doctype": "Employee Resignation Date Adjustment",
			"employee_resignation": self.resignation.name,
		}).insert()

		# Bypass the workflow engine's own transition check (Draft -> Pending
		# Supervisor is a valid single hop) to isolate the mandatory-field
		# check itself.
		ext.workflow_state = "Pending Supervisor"
		with self.assertRaises(frappe.ValidationError) as context:
			ext.save()
		self.assertTrue("Extended Relieving Date is mandatory" in str(context.exception))

	def test_extension_approval_side_effects(self):
		ext = frappe.get_doc({
			"doctype": "Employee Resignation Date Adjustment",
			"employee_resignation": self.resignation.name,
			"extended_relieving_date": self.extended_relieving_date,
		}).insert()

		# Corporate path: Pending Supervisor -> Approved directly, no T4/PM
		# routing involved -- isolates the approval side effects from the
		# branching logic other tests already cover.
		ext.db_set("is_corporate", 1, update_modified=False)
		ext.reload()
		ext.db_set("workflow_state", "Pending Supervisor", update_modified=False)
		ext.reload()

		ext.workflow_state = "Approved"
		ext.save()

		self.resignation.reload()
		self.employee.reload()
		self.pmr.reload()

		self.assertEqual(getdate(self.resignation.relieving_date), getdate(self.extended_relieving_date))
		self.assertEqual(getdate(self.employee.relieving_date), getdate(self.extended_relieving_date))
		self.assertEqual(getdate(self.pmr.deployment_date), getdate(frappe.utils.add_days(self.extended_relieving_date, -11)))


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
			"status": "Active",
			"project": _get_or_create_project("Test ERDA Project", company),
			"designation": _get_or_create_designation("Test ERDA Designation"),
		}).insert()
		return doc.name
	return existing


def _get_or_create_project(project_name, company):
	if not frappe.db.exists("Project", project_name):
		frappe.get_doc({
			"doctype": "Project",
			"project_name": project_name,
			"company": company,
		}).insert()
	return project_name


def _get_or_create_designation(designation_name):
	if not frappe.db.exists("Designation", designation_name):
		frappe.get_doc({
			"doctype": "Designation",
			"designation_name": designation_name,
		}).insert()
	return designation_name


def _get_or_create_department(department_name, company):
	company_abbr = frappe.get_cached_value("Company", company, "abbr") or company
	full_dept_name = f"{department_name} - {company_abbr}"

	if not frappe.db.exists("Department", full_dept_name):
		frappe.get_doc({
			"doctype": "Department",
			"department_name": department_name,
			"department_code": "TEST-DEPT-ERDA",
			"company": company,
		}).insert()
	return full_dept_name
