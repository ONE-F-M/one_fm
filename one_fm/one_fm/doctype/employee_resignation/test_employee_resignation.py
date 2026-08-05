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
		user.insert()
		return user.name

	def _make_employee(self, name_suffix, user_id=None, reports_to=None, site=None, project=None, department=None):
		"""Create a minimal Employee record for testing.

		Employee autonames via `naming_series:`, so the intended "TEST-RSGN-EMP-*"
		label is never actually the doc's real name -- dedup has to key off
		`user_id` (the actual uniqueness constraint Employee enforces) or
		`employee_name` instead, or every run/rerun creates a fresh Employee tied
		to the same fixed test email and fails with DuplicateEntryError.
		"""
		employee_name = f"Test Employee {name_suffix}"
		existing = None
		if user_id:
			existing = frappe.db.get_value("Employee", {"user_id": user_id}, "name")
		if not existing:
			existing = frappe.db.get_value("Employee", {"employee_name": employee_name}, "name")
		if existing:
			frappe.db.set_value("Employee", existing, {
				"reports_to": reports_to,
				"site": site,
				"project": project,
				"user_id": user_id
			})
			return existing

		company = frappe.db.get_single_value("Global Defaults", "default_company")
		if not company or not frappe.db.exists("Company", company):
			companies = frappe.get_all("Company", limit=1)
			company = companies[0].name if companies else "ONE FM"

		if not department:
			company_abbr = frappe.get_cached_value("Company", company, "abbr") or company
			department = f"Test Department - {company_abbr}"
			if not frappe.db.exists("Department", department):
				frappe.get_doc({
					"doctype": "Department",
					"department_name": "Test Department",
					"company": company
				}).insert()

		emp = frappe.get_doc({
			"doctype": "Employee",
			"employee_name": employee_name,
			"first_name": "Test",
			"last_name": f"Employee {name_suffix}",
			"gender": "Male",
			"date_of_birth": "1990-01-01",
			"date_of_joining": "2020-01-01",
			"status": "Active",
			"company": company,
			"department": department,
			"one_fm_basic_salary": 1000,
			"one_fm_first_name_in_arabic": "تيست",
			"one_fm_last_name_in_arabic": "موظف",
			"user_id": user_id,
			"reports_to": reports_to,
			"site": site,
			"project": project
		})
		emp.insert()
		return emp.name

	def _make_location(self):
		location_name = "TEST-RSGN-LOCATION"
		if not frappe.db.exists("Location", location_name):
			frappe.get_doc({
				"doctype": "Location",
				"location_name": location_name,
				"latitude": 29.3759,
				"longitude": 47.9774,
				"geofence_radius": 100,
			}).insert()
		return location_name

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
				"site_supervisor": site_sup_emp,
				"site_location": self._make_location(),
				"poc": [{}],
			})
			site_doc.insert()
		else:
			frappe.db.set_value("Operations Site", site_name, "site_supervisor", site_sup_emp)

		employee_emp = self._make_employee("EMP-B", site=site_name)

		doc = self._make_resignation(employee_emp)
		doc.set_supervisor()

		self.assertEqual(doc.supervisor, site_sup_user)

	def test_set_supervisor_via_project_manager(self):
		"""get_approver()'s fallback chain reaches Project Manager via the employee's
		Operations Site -> that site's Project -> the Project's project_manager --
		not via the Employee's own `project` field directly."""
		pm_user = self._make_user("test-rsgn-pm@example.com", "PM")
		pm_emp = self._make_employee("PM-EMP", user_id=pm_user)

		project_name = "TEST-RSGN-PROJECT"
		if not frappe.db.exists("Project", project_name):
			frappe.get_doc({
				"doctype": "Project",
				"project_name": project_name,
				"project_manager": pm_emp,
				"expected_start_date": "2026-01-01"
			}).insert()
		else:
			frappe.db.set_value("Project", project_name, "project_manager", pm_emp)

		site_name = "TEST-RSGN-PM-SITE"
		if not frappe.db.exists("Operations Site", site_name):
			frappe.get_doc({
				"doctype": "Operations Site",
				"site_name": site_name,
				"project": project_name,
				"site_location": self._make_location(),
				"poc": [{}],
			}).insert()
		else:
			frappe.db.set_value("Operations Site", site_name, {"project": project_name, "site_supervisor": None})

		employee_emp = self._make_employee("EMP-C", site=site_name)

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

	def test_shift_worker_requires_project_manager(self):
		"""Test that Pending Project Manager / Approved require a Project Manager to be set."""
		emp_name = "TEST-SHIFT-VAL-EMP"

		original_get_value = frappe.db.get_value
		def mock_get_value(doctype, filters=None, fieldname=None, *args, **kwargs):
			if doctype == "Employee" and filters == emp_name:
				if fieldname == ["site", "project", "department", "shift", "custom_operations_role_allocation", "shift_working"]:
					return frappe._dict({
						"site": "Test Site",
						"project": "Test Project",
						"department": "Operations Dept",
						"shift": "Test Shift",
						"custom_operations_role_allocation": "Test Role",
						"shift_working": 1
					})
				if fieldname == ["project", "designation", "employee_name"]:
					return frappe._dict({
						"project": "Test Project",
						"designation": "Test Designation",
						"employee_name": "Test Employee"
					})
			return original_get_value(doctype, filters, fieldname, *args, **kwargs)

		original_exists = frappe.db.exists
		def mock_exists(dt, name=None, *args, **kwargs):
			if dt == "Employee":
				if isinstance(name, dict) and name.get("name") in (emp_name, "TEST-SHIFT-VAL-EMP", "TEST-CORP-VAL-EMP"):
					return True
				if name in (emp_name, "TEST-SHIFT-VAL-EMP", "TEST-CORP-VAL-EMP"):
					return True
			return original_exists(dt, name, *args, **kwargs)

		frappe.db.get_value = mock_get_value
		frappe.db.exists = mock_exists
		try:
			doc = self._make_resignation(emp_name)
			doc.resignation_initiation_date = "2026-10-10"
			doc.relieving_date = "2026-10-15"
			# Pre-set so set_supervisor()'s get_approver() lookup is skipped entirely --
			# this test is about the Project Manager requirement, not supervisor resolution.
			doc.supervisor = "test-rsgn-manager@example.com"

			doc.workflow_state = "Pending Project Manager"
			doc.offboarding_officer = "test-rsgn-manager@example.com"
			doc.project_manager = ""

			# 1. Validation must fail because project_manager is empty
			with self.assertRaises(frappe.ValidationError) as context:
				doc.validate()
			self.assertIn("specify the <b>Project Manager</b>", str(context.exception))

			# 2. Validation must pass once project_manager is provided
			doc.project_manager = "test-rsgn-manager@example.com"
			doc.validate()
		finally:
			frappe.db.get_value = original_get_value
			frappe.db.exists = original_exists

	def test_replacement_details_required_when_replacement_yes(self):
		"""Nationality/Gender/Salary feed the auto-created PMR directly, so
		they must be filled in before approving once a replacement is
		confirmed as needed."""
		emp_name = "TEST-REPLACEMENT-VAL-EMP"

		original_get_value = frappe.db.get_value
		def mock_get_value(doctype, filters=None, fieldname=None, *args, **kwargs):
			if doctype == "Employee" and filters == emp_name:
				if fieldname == ["site", "project", "department", "shift", "custom_operations_role_allocation", "shift_working"]:
					return frappe._dict({
						"site": "Test Site",
						"project": "Test Project",
						"department": "Operations Dept",
						"shift": "Test Shift",
						"custom_operations_role_allocation": "Test Role",
						"shift_working": 1
					})
				if fieldname == ["project", "designation", "employee_name"]:
					return frappe._dict({
						"project": "Test Project",
						"designation": "Test Designation",
						"employee_name": "Test Employee"
					})
			return original_get_value(doctype, filters, fieldname, *args, **kwargs)

		original_exists = frappe.db.exists
		def mock_exists(dt, name=None, *args, **kwargs):
			if dt == "Employee":
				if isinstance(name, dict) and name.get("name") == emp_name:
					return True
				if name == emp_name:
					return True
			return original_exists(dt, name, *args, **kwargs)

		frappe.db.get_value = mock_get_value
		frappe.db.exists = mock_exists
		try:
			doc = self._make_resignation(emp_name)
			doc.resignation_initiation_date = "2026-10-10"
			doc.relieving_date = "2026-10-15"
			doc.supervisor = "test-rsgn-manager@example.com"
			doc.offboarding_officer = "test-rsgn-manager@example.com"
			doc.project_manager = "test-rsgn-manager@example.com"
			doc.workflow_state = "Pending Project Manager"
			doc.replacement_required = "Yes"

			with self.assertRaises(frappe.ValidationError) as context:
				doc.validate()
			self.assertIn("Replacement Nationality", str(context.exception))
			self.assertIn("Replacement Gender", str(context.exception))
			self.assertIn("Replacement Salary", str(context.exception))

			doc.replacement_nationality = "Any"
			doc.replacement_gender = "Any"
			doc.replacement_salary = 500
			doc.validate()  # must not raise
		finally:
			frappe.db.get_value = original_get_value
			frappe.db.exists = original_exists

	def test_non_shift_worker_never_reaches_project_manager_stage(self):
		"""Non-Shift (Line Manager) resignations skip Project Manager entirely --
		Approved never requires it when shift_working is 0."""
		emp_name = "TEST-CORP-VAL-EMP"

		original_get_value = frappe.db.get_value
		def mock_get_value(doctype, filters=None, fieldname=None, *args, **kwargs):
			if doctype == "Employee" and filters == emp_name:
				if fieldname == ["site", "project", "department", "shift", "custom_operations_role_allocation", "shift_working"]:
					return frappe._dict({
						"site": "Test Site",
						"project": "Test Project",
						"department": "Test Dept",
						"shift": "Test Shift",
						"custom_operations_role_allocation": "Test Role",
						"shift_working": 0
					})
				if fieldname == ["project", "designation", "employee_name"]:
					return frappe._dict({
						"project": "Test Project",
						"designation": "Test Designation",
						"employee_name": "Test Employee"
					})
			return original_get_value(doctype, filters, fieldname, *args, **kwargs)

		original_exists = frappe.db.exists
		def mock_exists(dt, name=None, *args, **kwargs):
			if dt == "Employee":
				if isinstance(name, dict) and name.get("name") in (emp_name, "TEST-SHIFT-VAL-EMP", "TEST-CORP-VAL-EMP"):
					return True
				if name in (emp_name, "TEST-SHIFT-VAL-EMP", "TEST-CORP-VAL-EMP"):
					return True
			return original_exists(dt, name, *args, **kwargs)

		frappe.db.get_value = mock_get_value
		frappe.db.exists = mock_exists
		try:
			doc = self._make_resignation(emp_name)
			doc.resignation_initiation_date = "2026-10-10"
			doc.relieving_date = "2026-10-15"
			doc.supervisor = "test-rsgn-manager@example.com"

			doc.workflow_state = "Approved"
			doc.offboarding_officer = "test-rsgn-manager@example.com"
			doc.project_manager = ""
			doc.negotiation_remarks = "Tried to retain, unsuccessful."
			doc.performance_remarks = "Solid performer."
			doc.complaints_remarks = "None."

			# Validation must pass: shift_working == 0 exempts Project Manager entirely,
			# and auto-sets replacement_required to "No".
			doc.validate()
			self.assertEqual(doc.replacement_required, "No")
		finally:
			frappe.db.get_value = original_get_value
			frappe.db.exists = original_exists

	# -- shift_category / t4_route (Project Allocation gateway) --
	# Department is a generic "Operations - ONEFM" bucket shared by every
	# shift-working employee whether they're T4 or not -- Project Allocation
	# is what actually distinguishes them (e.g. "T4 Airport").

	def test_shift_category_operations_when_project_not_t4(self):
		emp_name = "TEST-SHIFTCAT-OPS-EMP"

		original_get_value = frappe.db.get_value
		def mock_get_value(doctype, filters=None, fieldname=None, *args, **kwargs):
			if doctype == "Employee" and filters == emp_name:
				if fieldname == ["site", "project", "department", "shift", "custom_operations_role_allocation", "shift_working"]:
					return frappe._dict({
						"site": "Test Site",
						"project": "Al-Babtain",
						"department": "Operations - ONEFM",
						"shift": "Test Shift",
						"custom_operations_role_allocation": "Test Role",
						"shift_working": 1
					})
			return original_get_value(doctype, filters, fieldname, *args, **kwargs)

		frappe.db.get_value = mock_get_value
		try:
			doc = frappe.new_doc("Employee Resignation")
			doc.employee = emp_name
			doc.set_allocations()
			self.assertEqual(doc.shift_category, "Operations")
		finally:
			frappe.db.get_value = original_get_value

	def test_shift_category_t4_when_project_contains_t4(self):
		emp_name = "TEST-SHIFTCAT-T4-EMP"

		original_get_value = frappe.db.get_value
		def mock_get_value(doctype, filters=None, fieldname=None, *args, **kwargs):
			if doctype == "Employee" and filters == emp_name:
				if fieldname == ["site", "project", "department", "shift", "custom_operations_role_allocation", "shift_working"]:
					return frappe._dict({
						"site": "Test Site",
						"project": "T4 Airport",
						"department": "Operations - ONEFM",
						"shift": "Test Shift",
						"custom_operations_role_allocation": "Test Role",
						"shift_working": 1
					})
			return original_get_value(doctype, filters, fieldname, *args, **kwargs)

		frappe.db.get_value = mock_get_value
		try:
			doc = frappe.new_doc("Employee Resignation")
			doc.employee = emp_name
			doc.set_allocations()
			self.assertEqual(doc.shift_category, "T4")
		finally:
			frappe.db.get_value = original_get_value

	def test_classify_t4_route_security(self):
		doc = frappe.new_doc("Employee Resignation")
		doc.shift_category = "T4"
		doc.designation = "Security Guard"
		doc.classify_t4_route()
		self.assertEqual(doc.t4_route, "Security")

	def test_classify_t4_route_janitorial(self):
		doc = frappe.new_doc("Employee Resignation")
		doc.shift_category = "T4"
		doc.designation = "Janitor"
		doc.classify_t4_route()
		self.assertEqual(doc.t4_route, "Janitorial")

	def test_create_pmr_notifies_t4_admin_for_any_t4_route(self):
		"""All three T4 routes (Security, Janitorial, Passenger-Customer
		Service) auto-create the PMR the same way -- T4 Admin is just
		notified to review and submit it to the recruiter, rather than
		Passenger-Customer Service being the one route where the PMR isn't
		auto-created at all."""
		t4_admin_user = self._make_user("test-rsgn-t4admin@example.com", "T4 Admin")

		project_name = "TEST-RSGN-T4-PMR-PROJECT"
		if not frappe.db.exists("Project", project_name):
			frappe.get_doc({
				"doctype": "Project",
				"project_name": project_name,
				"expected_start_date": "2026-01-01"
			}).insert()

		employee_emp = self._make_employee("T4-PMR-EMP", project=project_name)
		frappe.db.set_value("Employee", employee_emp, "designation", "Passenger Service Coordinator")

		doc = self._make_resignation(employee_emp)
		doc.project_allocation = project_name
		doc.resignation_initiation_date = "2026-12-01"
		doc.shift_working = 1
		doc.shift_category = "T4"
		doc.t4_route = "Passenger-Customer Service"
		doc.t4_admin = t4_admin_user
		doc.replacement_priority = "Medium"
		doc.insert()

		doc.create_pmr()

		pmr_name = frappe.db.get_value(
			"Project Manpower Request", {"employee_resignation": doc.name}, "name"
		)
		self.assertIsNotNone(pmr_name)
		self.assertEqual(frappe.db.get_value("Project Manpower Request", pmr_name, "workflow_state"), "Draft")

		todo_exists = frappe.db.exists("ToDo", {
			"reference_type": "Project Manpower Request",
			"reference_name": pmr_name,
			"allocated_to": t4_admin_user
		})
		self.assertTrue(todo_exists)

	def test_relieving_date_correction_assigns_employee(self):
		"""Frappe defaults to assigning whoever triggers a workflow
		transition when nothing else is explicitly assigned -- without
		assign_employee_for_relieving_date_correction(), a "Request
		Relieving Date Change" would leave the ToDo with that actor instead
		of the employee who actually needs to fix their own date."""
		project_name = "TEST-RSGN-RDC-PROJECT"
		if not frappe.db.exists("Project", project_name):
			frappe.get_doc({
				"doctype": "Project",
				"project_name": project_name,
				"expected_start_date": "2026-01-01"
			}).insert()

		user_id = self._make_user(f"test_rdc_{frappe.generate_hash(length=8)}@example.com", "RDC Employee")
		employee_emp = self._make_employee("RDC-EMP", user_id=user_id, project=project_name)
		frappe.db.set_value("Employee", employee_emp, "designation", "Passenger Service Coordinator")

		doc = self._make_resignation(employee_emp)
		doc.resignation_initiation_date = "2026-12-01"
		doc.insert()

		# "Request Relieving Date Change" is only a valid transition from a
		# real review state, not directly from Draft -- db_set past that
		# check, mirroring the states[0]-bypass pattern used elsewhere.
		doc.db_set("workflow_state", "Pending Supervisor", update_modified=False)
		doc.reload()

		# Simulate Frappe's default behavior: whoever triggers "Request
		# Relieving Date Change" gets auto-assigned in the absence of any
		# explicit assignment.
		from frappe.desk.form.assign_to import add as add_assignment
		add_assignment({
			"doctype": "Employee Resignation",
			"name": doc.name,
			"assign_to": ["Administrator"],
		})

		doc.workflow_state = "Pending Relieving Date Correction"
		doc.flags.ignore_mandatory = True
		doc.save()

		admin_todo_open = frappe.db.exists("ToDo", {
			"reference_type": "Employee Resignation", "reference_name": doc.name,
			"allocated_to": "Administrator", "status": "Open"
		})
		self.assertFalse(admin_todo_open)

		employee_todo_open = frappe.db.exists("ToDo", {
			"reference_type": "Employee Resignation", "reference_name": doc.name,
			"allocated_to": user_id, "status": "Open"
		})
		self.assertTrue(employee_todo_open)

	def test_classify_t4_route_cleaner_is_janitorial(self):
		"""Real designation data uses "Cleaner"/"Cleaner Supervisor", not
		"Janitor" -- both must route the same way."""
		doc = frappe.new_doc("Employee Resignation")
		doc.shift_category = "T4"
		doc.designation = "Cleaner Supervisor"
		doc.classify_t4_route()
		self.assertEqual(doc.t4_route, "Janitorial")

	def test_classify_t4_route_passenger_customer_service_default(self):
		doc = frappe.new_doc("Employee Resignation")
		doc.shift_category = "T4"
		doc.designation = "Customer Service Agent"
		doc.classify_t4_route()
		self.assertEqual(doc.t4_route, "Passenger-Customer Service")

	def test_classify_t4_route_blank_outside_t4(self):
		"""Operations and Non-Shift resignations never get a t4_route."""
		doc = frappe.new_doc("Employee Resignation")
		doc.shift_category = "Operations"
		doc.designation = "Security Guard"  # even a security-sounding designation
		doc.classify_t4_route()
		self.assertIsNone(doc.t4_route)

	# -- Remarks bundle: required before leaving any review stage --

	def test_validate_step_remarks_blocks_without_all_three_fields(self):
		employee_emp = self._make_employee("EMP-REMARKS-BLOCK")
		doc = self._make_resignation(employee_emp)
		doc.workflow_state = "Pending Project Manager"

		class _FakeBefore:
			def get(self, key, default=None):
				return "Pending Supervisor" if key == "workflow_state" else default

		doc.get_doc_before_save = lambda: _FakeBefore()
		doc.negotiation_remarks = "Tried to retain, unsuccessful."
		# performance_remarks / complaints_remarks left blank on purpose

		with self.assertRaises(frappe.ValidationError) as context:
			doc.validate_step_remarks()
		self.assertIn("Pending Supervisor", str(context.exception))

	def test_validate_step_remarks_passes_with_all_three_fields(self):
		employee_emp = self._make_employee("EMP-REMARKS-OK")
		doc = self._make_resignation(employee_emp)
		doc.workflow_state = "Pending Project Manager"

		class _FakeBefore:
			def get(self, key, default=None):
				return "Pending Supervisor" if key == "workflow_state" else default

		doc.get_doc_before_save = lambda: _FakeBefore()
		doc.negotiation_remarks = "Tried to retain, unsuccessful."
		doc.performance_remarks = "Solid performer."
		doc.complaints_remarks = "None."

		doc.validate_step_remarks()  # must not raise
		self.assertIsNone(doc.negotiation_remarks)
		self.assertIsNone(doc.performance_remarks)
		self.assertIsNone(doc.complaints_remarks)
		self.assertIn("Supervisor:", doc.remarks_log)
		self.assertIn("Solid performer.", doc.remarks_log)

	def test_validate_step_remarks_accumulates_full_chain(self):
		"""Remarks History keeps every departed stage's entry, in order --
		not just the most recent one."""
		employee_emp = self._make_employee("EMP-REMARKS-CHAIN")
		doc = self._make_resignation(employee_emp)

		doc.workflow_state = "Pending T4 Admin"

		class _FakeBeforeSupervisor:
			def get(self, key, default=None):
				return "Pending Supervisor" if key == "workflow_state" else default

		doc.get_doc_before_save = lambda: _FakeBeforeSupervisor()
		doc.negotiation_remarks = "First round negotiation."
		doc.performance_remarks = "First round performance."
		doc.complaints_remarks = "First round complaints."
		doc.validate_step_remarks()

		doc.workflow_state = "Pending Project Manager"

		class _FakeBeforeT4Admin:
			def get(self, key, default=None):
				return "Pending T4 Admin" if key == "workflow_state" else default

		doc.get_doc_before_save = lambda: _FakeBeforeT4Admin()
		doc.negotiation_remarks = "Second round negotiation."
		doc.performance_remarks = "Second round performance."
		doc.complaints_remarks = "Second round complaints."
		doc.validate_step_remarks()

		self.assertIn("Supervisor:", doc.remarks_log)
		self.assertIn("First round negotiation.", doc.remarks_log)
		self.assertIn("T4 Admin:", doc.remarks_log)
		self.assertIn("Second round negotiation.", doc.remarks_log)
		self.assertLess(doc.remarks_log.index("Supervisor:"), doc.remarks_log.index("T4 Admin:"))

	# -- Current salary auto-fetch --

	def test_set_current_salary_fetches_latest_assignment(self):
		employee_emp = self._make_employee("EMP-SALARY")

		if not frappe.db.exists("Salary Structure", "TEST-RSGN-STRUCT"):
			frappe.get_doc({
				"doctype": "Salary Structure",
				"name": "TEST-RSGN-STRUCT",
				"salary_structure_name": "TEST-RSGN-STRUCT",
				"company": frappe.db.get_value("Employee", employee_emp, "company"),
				"is_active": "Yes",
			}).insert(ignore_mandatory=True)

		if not frappe.db.exists("Salary Structure Assignment", {"employee": employee_emp, "from_date": "2020-01-01"}):
			assignment = frappe.get_doc({
				"doctype": "Salary Structure Assignment",
				"employee": employee_emp,
				"salary_structure": "TEST-RSGN-STRUCT",
				"from_date": "2020-01-01",
				"company": frappe.db.get_value("Employee", employee_emp, "company"),
				"base": 5000,
			})
			assignment.insert(ignore_mandatory=True)
			assignment.submit()

		doc = self._make_resignation(employee_emp)
		doc.set_current_salary()
		self.assertEqual(doc.current_salary, 5000)
