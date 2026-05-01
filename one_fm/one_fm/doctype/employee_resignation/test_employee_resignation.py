# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestEmployeeResignation(FrappeTestCase):
	"""Unit tests for the EmployeeResignation controller's set_supervisor logic."""

	def _make_user(self, email, first_name="Test"):
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

	def _make_employee(self, name_suffix, user_id=None, reports_to=None, site=None, project=None):
		"""Create a minimal Employee record for testing."""
		emp_name = f"TEST-RSGN-EMP-{name_suffix}"
		if frappe.db.exists("Employee", emp_name):
			frappe.db.set_value("Employee", emp_name, {
				"reports_to": reports_to,
				"site": site,
				"project": project,
				"user_id": user_id
			})
			return emp_name

		company = frappe.db.get_single_value("Global Defaults", "default_company") or "ONE FM"
		emp = frappe.get_doc({
			"doctype": "Employee",
			"employee": emp_name,
			"first_name": "Test",
			"last_name": f"Employee {name_suffix}",
			"gender": "Male",
			"date_of_birth": "1990-01-01",
			"date_of_joining": "2020-01-01",
			"status": "Active",
			"company": company,
			"one_fm_first_name_in_arabic": "تيست",
			"one_fm_last_name_in_arabic": "موظف",
			"user_id": user_id,
			"reports_to": reports_to,
			"site": site,
			"project": project
		})
		emp.insert(ignore_permissions=True)
		return emp.name

	def _make_resignation(self, employee):
		"""Create a minimal (unsaved) EmployeeResignation doc for testing."""
		doc = frappe.new_doc("Employee Resignation")
		doc.employee = employee
		doc.relieving_date = "2026-12-31"
		doc.resignation_letter = "/files/test_letter.pdf"
		doc.full_name_in_english = "Test Employee"
		return doc

	def test_set_supervisor_via_reports_to(self):
		"""Supervisor set from reports_to.user_id (highest priority)."""
		manager_user = self._make_user("test-rsgn-manager@example.com", "Manager")
		manager_emp = self._make_employee("MGR", user_id=manager_user)
		employee_emp = self._make_employee("EMP-A", reports_to=manager_emp)

		doc = self._make_resignation(employee_emp)
		doc.set_supervisor()

		self.assertEqual(doc.supervisor, manager_user)

	def test_set_supervisor_via_site_supervisor(self):
		"""Supervisor falls back to site_supervisor.user_id when reports_to is absent."""
		site_sup_user = self._make_user("test-rsgn-sitesup@example.com", "Site Sup")
		site_sup_emp = self._make_employee("SITE-SUP", user_id=site_sup_user)

		# Create a bare-minimum Operations Site with a site_supervisor
		site_name = "TEST-RSGN-SITE"
		if not frappe.db.exists("Operations Site", site_name):
			site_doc = frappe.get_doc({
				"doctype": "Operations Site",
				"site_name": site_name,
				"site_supervisor": site_sup_emp
			})
			site_doc.insert(ignore_permissions=True)
		else:
			frappe.db.set_value("Operations Site", site_name, "site_supervisor", site_sup_emp)

		employee_emp = self._make_employee("EMP-B", site=site_name)

		doc = self._make_resignation(employee_emp)
		doc.set_supervisor()

		self.assertEqual(doc.supervisor, site_sup_user)

	def test_set_supervisor_via_project_manager(self):
		"""Supervisor falls back to project_manager.user_id when reports_to and site are absent."""
		pm_user = self._make_user("test-rsgn-pm@example.com", "PM")
		pm_emp = self._make_employee("PM-EMP", user_id=pm_user)

		project_name = "TEST-RSGN-PROJECT"
		if not frappe.db.exists("Project", project_name):
			frappe.get_doc({
				"doctype": "Project",
				"project_name": project_name,
				"project_manager": pm_emp,
				"expected_start_date": "2026-01-01"
			}).insert(ignore_permissions=True)
		else:
			frappe.db.set_value("Project", project_name, "project_manager", pm_emp)

		employee_emp = self._make_employee("EMP-C", project=project_name)

		doc = self._make_resignation(employee_emp)
		doc.set_supervisor()

		self.assertEqual(doc.supervisor, pm_user)

	def test_set_supervisor_does_not_overwrite_existing(self):
		"""set_supervisor skips auto-fill if supervisor is already populated."""
		manager_user = self._make_user("test-rsgn-mgr2@example.com", "Manager 2")
		manager_emp = self._make_employee("MGR2", user_id=manager_user)
		employee_emp = self._make_employee("EMP-D", reports_to=manager_emp)

		existing_user = self._make_user("existing-super@example.com", "Existing")

		doc = self._make_resignation(employee_emp)
		doc.supervisor = existing_user
		doc.set_supervisor()

		# Must remain unchanged
		self.assertEqual(doc.supervisor, existing_user)

	def test_set_supervisor_no_employee_does_nothing(self):
		"""set_supervisor is a no-op when employee field is blank."""
		doc = frappe.new_doc("Employee Resignation")
		doc.employee = None
		doc.supervisor = None
		doc.set_supervisor()
		self.assertIsNone(doc.supervisor)

	def test_validate_dates_invalid(self):
		"""Test validate_dates() with an invalid date range."""
		employee_emp = self._make_employee("EMP-VAL-DATES")
		doc = self._make_resignation(employee_emp)
		
		# Relieving date set BEFORE initiation date
		doc.resignation_initiation_date = "2026-10-15"
		doc.relieving_date = "2026-10-10"
		
		with self.assertRaises(frappe.ValidationError) as context:
			doc.validate_dates()
		
		self.assertTrue("Relieving Date cannot be before Resignation Initiation Date" in str(context.exception))

	def test_api_create_resignation_missing_attachment(self):
		"""Test that create_resignation API rejects submissions missing attachments."""
		from one_fm.api.v1.resignation import create_resignation
		
		employee_emp = self._make_employee("API-TEST-NO-ATT")
		
		with self.assertRaises(frappe.ValidationError) as context:
			create_resignation(
				employee_id=employee_emp,
				resignation_initiation_date="2026-04-01",
				relieving_date="2026-05-01",
				attachment=None
			)
		
		self.assertTrue("A resignation letter attachment is mandatory." in str(context.exception))
