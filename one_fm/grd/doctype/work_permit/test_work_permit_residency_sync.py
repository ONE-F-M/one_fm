# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-003158: a Completed Work Permit puts the Employee under company residency (and
flips the residency digit of the display employee_id); a Completed Cancellation takes
them out again. The HR-EMP name never changes."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

# YYMM + serial + country + residency digit + birth year; the digit is 3rd from last.
ID_NOT_UNDER_RESIDENCY = "2609051NP086"
ID_UNDER_RESIDENCY = "2609051NP186"
ID_SUBCONTRACT = "2609051NPS86"

IS_SUBCONTRACT = "one_fm.overrides.employee.is_subcontract_employee"


def _an_active_employee():
	name = frappe.db.get_value(
		"Employee",
		{"status": "Active", "relieving_date": ["is", "not set"]},
		"name",
		order_by="creation asc",
	)
	if not name:
		raise frappe.DoesNotExistError("No active employee on this site to test against")
	return name


class TestWorkPermitResidencySync(FrappeTestCase):
	def setUp(self):
		self.employee = _an_active_employee()
		self.before = frappe.db.get_value(
			"Employee", self.employee, ["employee_id", "under_company_residency"], as_dict=True
		)

	def tearDown(self):
		frappe.db.set_value(
			"Employee",
			self.employee,
			{
				"employee_id": self.before.employee_id,
				"under_company_residency": self.before.under_company_residency,
			},
			update_modified=False,
		)

	def _employee_is(self, employee_id, under_company_residency):
		frappe.db.set_value(
			"Employee",
			self.employee,
			{"employee_id": employee_id, "under_company_residency": under_company_residency},
			update_modified=False,
		)

	def _complete(self, work_permit_type, workflow_state="Completed"):
		permit = frappe.new_doc("Work Permit")
		permit.employee = self.employee
		permit.work_permit_type = work_permit_type
		permit.workflow_state = workflow_state
		permit.set_new_pam_details_in_employee()
		return frappe.db.get_value(
			"Employee",
			self.employee,
			["name", "employee_id", "under_company_residency"],
			as_dict=True,
		)

	@patch(IS_SUBCONTRACT, return_value=False)
	def test_completed_renewal_expat_puts_the_employee_under_residency(self, _):
		self._employee_is(ID_NOT_UNDER_RESIDENCY, 0)

		after = self._complete("Renewal Expat")

		self.assertEqual(after.under_company_residency, 1)
		self.assertEqual(after.employee_id, ID_UNDER_RESIDENCY)
		self.assertEqual(after.name, self.employee)

	@patch(IS_SUBCONTRACT, return_value=False)
	def test_a_permit_that_is_not_completed_changes_nothing(self, _):
		self._employee_is(ID_NOT_UNDER_RESIDENCY, 0)

		after = self._complete("Renewal Expat", workflow_state="Pending by GR Operator")

		self.assertEqual(after.under_company_residency, 0)
		self.assertEqual(after.employee_id, ID_NOT_UNDER_RESIDENCY)

	@patch(IS_SUBCONTRACT, return_value=False)
	def test_completed_renewal_kuwaiti_changes_nothing(self, _):
		self._employee_is(ID_NOT_UNDER_RESIDENCY, 0)

		for permit_type in ("Renewal Kuwaiti", "New Kuwaiti"):
			after = self._complete(permit_type)

			self.assertEqual(after.under_company_residency, 0, permit_type)
			self.assertEqual(after.employee_id, ID_NOT_UNDER_RESIDENCY, permit_type)

	@patch(IS_SUBCONTRACT, return_value=True)
	def test_a_subcontractor_keeps_the_s(self, _):
		self._employee_is(ID_SUBCONTRACT, 0)

		after = self._complete("Renewal Expat")

		self.assertEqual(after.under_company_residency, 1)
		self.assertEqual(after.employee_id, ID_SUBCONTRACT)

	@patch(IS_SUBCONTRACT, return_value=False)
	def test_completed_cancellation_takes_the_employee_out_of_residency(self, _):
		self._employee_is(ID_UNDER_RESIDENCY, 1)

		after = self._complete("Cancellation")

		self.assertEqual(after.under_company_residency, 0)
		self.assertEqual(after.employee_id, ID_NOT_UNDER_RESIDENCY)
		self.assertEqual(after.name, self.employee)

	@patch(IS_SUBCONTRACT, return_value=False)
	def test_a_cancellation_that_is_not_completed_changes_nothing(self, _):
		self._employee_is(ID_UNDER_RESIDENCY, 1)

		after = self._complete("Cancellation", workflow_state="Pending By PAM")

		self.assertEqual(after.under_company_residency, 1)
		self.assertEqual(after.employee_id, ID_UNDER_RESIDENCY)
