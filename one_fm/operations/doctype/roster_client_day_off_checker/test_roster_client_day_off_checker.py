# Copyright (c) 2026, ONE FM and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.operations.doctype.roster_client_day_off_checker.roster_client_day_off_checker import (
	get_take_action_data,
)

MODULE = "one_fm.operations.doctype.roster_client_day_off_checker.roster_client_day_off_checker"


class StubChecker(frappe._dict):
	"""Stand-in for the checker document.

	A module-level class rather than a _dict carrying a lambda: Frappe pickles values it
	caches, and a locally defined lambda cannot be pickled.
	"""

	def check_permission(self, *args, **kwargs):
		return None


class TestRosterClientDayOffChecker(FrappeTestCase):
	pass


class TestTakeActionData(FrappeTestCase):
	"""
	WI-001690: Take Action opens the roster pre-filtered by employee, project, site, shift
	and role. The checker document and Employee lookup are stubbed so the filter
	resolution is tested without Employee/Operations fixtures.
	"""

	def _checker(self, **overrides):
		doc = StubChecker(
			{
				"name": "OPR-RCDOC-TEST",
				"employee": "EMP-TEST-0001",
				"employee_id": "EMPID-1",
				"employee_name": "Test Worker",
				"project_allocation": "Project A",
				"site_allocation": "Site A",
				"shift_allocation": "Shift A",
				"date": "2026-07-11",
			}
		)
		doc.update(overrides)
		return doc

	def _employee(self, **overrides):
		employee = frappe._dict(
			{
				"project": "Employee Project",
				"site": "Employee Site",
				"shift": "Employee Shift",
				"custom_operations_role_allocation": "Role A",
				"employee_id": "EMPID-FALLBACK",
				"employee_name": "Fallback Name",
			}
		)
		employee.update(overrides)
		return employee

	def _run(self, checker=None, employee="default"):
		employee_value = self._employee() if employee == "default" else employee
		with patch(f"{MODULE}.frappe.get_doc", return_value=checker or self._checker()):
			with patch(f"{MODULE}.frappe.db.get_value", return_value=employee_value):
				return get_take_action_data("OPR-RCDOC-TEST")

	def test_every_filter_the_ac_asks_for_is_returned(self):
		params = self._run()["params"]

		# AC: Employee Name & ID, Project, Site, Shift, Role
		self.assertEqual(params["employee_id"], "EMPID-1")
		self.assertEqual(params["employee_name"], "Test Worker")
		self.assertEqual(params["project"], "Project A")
		self.assertEqual(params["site"], "Site A")
		self.assertEqual(params["shift"], "Shift A")
		self.assertEqual(params["operations_role"], "Role A")

	def test_redirects_to_the_roster(self):
		result = self._run()

		self.assertEqual(result["path"], "/app/roster")
		# These two open the right view; the rest are read by setup_staff_filters().
		self.assertEqual(result["params"]["main_view"], "roster")
		self.assertEqual(result["params"]["sub_view"], "roster")

	def test_calendar_opens_on_the_checker_month(self):
		params = self._run()["params"]

		self.assertEqual(params["year"], "2026")
		self.assertEqual(params["month"], "7")

	def test_allocations_fall_back_to_the_employee_record(self):
		# The checker stores allocations as free text and they can be blank. The Employee
		# record is the fallback, and is the only source for the operations role.
		checker = self._checker(project_allocation="", site_allocation=None, shift_allocation="")
		params = self._run(checker=checker)["params"]

		self.assertEqual(params["project"], "Employee Project")
		self.assertEqual(params["site"], "Employee Site")
		self.assertEqual(params["shift"], "Employee Shift")
		self.assertEqual(params["operations_role"], "Role A")

	def test_employee_identity_falls_back_too(self):
		checker = self._checker(employee_id="", employee_name="")
		params = self._run(checker=checker)["params"]

		self.assertEqual(params["employee_id"], "EMPID-FALLBACK")
		self.assertEqual(params["employee_name"], "Fallback Name")

	def test_missing_employee_record_does_not_raise(self):
		# get_value returns None when the Employee is gone. The button should still open
		# the roster with whatever the checker itself holds rather than erroring.
		params = self._run(employee=None)["params"]

		self.assertEqual(params["project"], "Project A")
		self.assertIsNone(params["operations_role"])

	def test_no_date_falls_back_to_today(self):
		checker = self._checker(date=None)
		params = self._run(checker=checker)["params"]

		today = frappe.utils.getdate(frappe.utils.nowdate())
		self.assertEqual(params["year"], str(today.year))
		self.assertEqual(params["month"], str(today.month))
