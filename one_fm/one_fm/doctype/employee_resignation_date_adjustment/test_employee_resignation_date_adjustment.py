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

	def test_project_manager_follows_the_employee_current_project(self):
		stale_user = "test_erda_stale_pm@example.com"
		if not frappe.db.exists("User", stale_user):
			frappe.get_doc({"doctype": "User", "email": stale_user, "first_name": "Stale PM", "send_welcome_email": 0}).insert()
		frappe.db.set_value("Employee Resignation", self.resignation.name, "project_manager", stale_user)

		new_pm_user = "test_erda_new_pm@example.com"
		if not frappe.db.exists("User", new_pm_user):
			frappe.get_doc({"doctype": "User", "email": new_pm_user, "first_name": "New PM", "send_welcome_email": 0}).insert()
		new_pm = _make_employee(new_pm_user, "Test ERDA New PM")
		frappe.db.set_value("Employee", new_pm, "user_id", new_pm_user)
		frappe.db.set_value("Project", self.employee.project, "project_manager", new_pm)

		ext = frappe.get_doc({
			"doctype": "Employee Resignation Date Adjustment",
			"employee_resignation": self.resignation.name,
		}).insert()

		self.assertEqual(ext.project_manager, new_pm_user)

	def test_supervisor_uses_the_same_lookup_as_the_withdrawal(self):
		from one_fm.utils import get_approver_user

		resignation_supervisor = _make_user("test_erda_resignation_supervisor@example.com")
		frappe.db.set_value("Employee Resignation", self.resignation.name, "supervisor", resignation_supervisor)
		frappe.db.set_value("Employee", self.employee.name, {"reports_to": None, "site": None})
		pm = _make_employee("test_erda_pm@example.com", "Test ERDA PM")
		frappe.db.set_value("Employee", pm, "user_id", _make_user("test_erda_pm@example.com"))
		frappe.db.set_value("Project", self.employee.project, "project_manager", pm)

		ext = frappe.get_doc({
			"doctype": "Employee Resignation Date Adjustment",
			"employee_resignation": self.resignation.name,
		}).insert()

		self.assertIsNone(get_approver_user(self.employee.name, skip_shift_supervisor=True))
		self.assertEqual(ext.supervisor, resignation_supervisor)
		self.assertEqual(ext.project_manager, "test_erda_pm@example.com")

	def test_project_manager_falls_back_to_the_resignation_when_none_is_current(self):
		resignation_pm = _make_user("test_erda_resignation_pm@example.com")
		frappe.db.set_value("Employee Resignation", self.resignation.name, "project_manager", resignation_pm)
		frappe.db.set_value("Project", self.employee.project, "project_manager", None)

		ext = frappe.get_doc({
			"doctype": "Employee Resignation Date Adjustment",
			"employee_resignation": self.resignation.name,
		}).insert()

		self.assertEqual(ext.project_manager, resignation_pm)

	def test_an_approved_date_adjustment_keeps_the_approvers_who_acted_on_it(self):
		ext = frappe.get_doc({
			"doctype": "Employee Resignation Date Adjustment",
			"employee_resignation": self.resignation.name,
			"extended_relieving_date": self.extended_relieving_date,
		}).insert()
		approver = _make_user("test_erda_old_supervisor@example.com")
		ext.db_set({"supervisor": approver, "workflow_state": "Approved"})
		new_supervisor = _make_employee("test_erda_new_supervisor@example.com", "Test ERDA New Supervisor")
		frappe.db.set_value("Employee", new_supervisor, "user_id", _make_user("test_erda_new_supervisor@example.com"))
		frappe.db.set_value("Employee", self.employee.name, "reports_to", new_supervisor)

		ext.reload()
		ext.save()

		self.assertEqual(ext.supervisor, approver)

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


def _make_user(email):
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}).insert()
	return email
