# Copyright (c) 2026, ONEFM and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_first_day, get_last_day, getdate

from one_fm.one_fm.doctype.proof_of_work.proof_of_work import (
	generate_proof_of_work,
	get_eligible_contracts,
)

TEST_YEAR = 2025
TEST_MONTH = 6


def _get_company():
	return frappe.db.get_value("Company", {}, "name")


def _get_or_create_customer():
	name = frappe.db.get_value("Customer", {}, "name")
	if name:
		return name
	customer = frappe.get_doc(
		{"doctype": "Customer", "customer_name": "_Test POW Customer"}
	).insert(ignore_permissions=True)
	return customer.name


class TestProofofWork(FrappeTestCase):
	def setUp(self):
		self.company = _get_company()
		self.customer = _get_or_create_customer()

		# Project the contract and attendance both point to.
		self.project = frappe.get_doc(
			{
				"doctype": "Project",
				"project_name": "_Test POW Project",
				"company": self.company,
			}
		).insert(ignore_permissions=True)

		# Active contract on that project.
		self.contract = frappe.get_doc(
			{
				"doctype": "Contracts",
				"client": self.customer,
				"project": self.project.name,
				"price_list": frappe.db.get_value("Price List", {}, "name"),
				"start_date": getdate(f"{TEST_YEAR}-01-01"),
			}
		).insert(ignore_permissions=True)
		self.contract.db_set("workflow_state", "Active")

		self.first_day = get_first_day(getdate(f"{TEST_YEAR}-{TEST_MONTH:02d}-01"))
		self.last_day = get_last_day(self.first_day)

		self._make_attendance()

	def _make_attendance(self):
		"""Insert a bare attendance row (bypassing the heavy controller) for the project."""
		att = frappe.new_doc("Attendance")
		att.naming_series = "HR-ATT-.YYYY.-"
		att.employee = "_TEST-POW-EMP"
		att.status = "Present"
		att.working_hours = 8
		att.attendance_date = self.first_day
		att.company = self.company
		att.project = self.project.name
		att.docstatus = 1
		att.name = f"POW-TEST-ATT-{self.project.name}"
		att.db_insert()

	# --- get_eligible_contracts -------------------------------------------------

	def test_eligible_contract_listed_and_not_ticked_when_pow_exists(self):
		rows = get_eligible_contracts(TEST_MONTH, TEST_YEAR)
		names = {r["name"]: r for r in rows}
		self.assertIn(self.contract.name, names)
		# No POW yet -> should be pre-ticked (has_pow == 0)
		self.assertEqual(names[self.contract.name]["has_pow"], 0)

		# After generating, the same contract should report has_pow == 1
		generate_proof_of_work(TEST_MONTH, TEST_YEAR, "Shift Hours", [self.contract.name])
		rows = get_eligible_contracts(TEST_MONTH, TEST_YEAR)
		names = {r["name"]: r for r in rows}
		self.assertEqual(names[self.contract.name]["has_pow"], 1)

	def test_contract_without_attendance_not_listed(self):
		# A month with no attendance should not surface the contract.
		rows = get_eligible_contracts(TEST_MONTH + 1, TEST_YEAR)
		self.assertNotIn(self.contract.name, {r["name"] for r in rows})

	# --- generate_proof_of_work -------------------------------------------------

	def test_generate_creates_header_record(self):
		res = generate_proof_of_work(
			TEST_MONTH, TEST_YEAR, "Both", [self.contract.name]
		)
		self.assertEqual(len(res["created"]), 1)

		pow_doc = frappe.get_doc("Proof of Work", res["created"][0])
		self.assertEqual(pow_doc.contract, self.contract.name)
		self.assertEqual(pow_doc.project, self.project.name)
		self.assertEqual(pow_doc.customer, self.customer)
		self.assertEqual(pow_doc.generation_basis, "Both")
		self.assertEqual(getdate(pow_doc.start_date), self.first_day)
		self.assertEqual(getdate(pow_doc.end_date), self.last_day)
		# Header only for this story — no child items.
		self.assertEqual(len(pow_doc.proof_of_work_item), 0)

	def test_generate_skips_duplicate(self):
		generate_proof_of_work(TEST_MONTH, TEST_YEAR, "Shift Hours", [self.contract.name])
		res = generate_proof_of_work(
			TEST_MONTH, TEST_YEAR, "Shift Hours", [self.contract.name]
		)
		self.assertEqual(len(res["created"]), 0)
		self.assertEqual(len(res["skipped"]), 1)
		self.assertEqual(res["skipped"][0]["contract"], self.contract.name)

	def test_generate_rejects_invalid_basis(self):
		with self.assertRaises(frappe.ValidationError):
			generate_proof_of_work(TEST_MONTH, TEST_YEAR, "Nonsense", [self.contract.name])

	def test_generate_rejects_empty_selection(self):
		with self.assertRaises(frappe.ValidationError):
			generate_proof_of_work(TEST_MONTH, TEST_YEAR, "Shift Hours", [])

	def test_generate_rejects_invalid_month(self):
		with self.assertRaises(frappe.ValidationError):
			generate_proof_of_work(13, TEST_YEAR, "Shift Hours", [self.contract.name])
