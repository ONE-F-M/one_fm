# Copyright (c) 2026, ONEFM and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_first_day, get_last_day, getdate

from one_fm.one_fm.doctype.proof_of_work.proof_of_work import (
	_shift_hours_from_item,
	generate_proof_of_work,
	get_eligible_contracts,
	resolve_attendance_source,
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


def _get_or_create_project(company):
	# Reused as a stable fixture: Project is named after project_name, so a
	# committed leftover from an earlier run would otherwise clash on insert.
	name = "_Test POW Project"
	if frappe.db.exists("Project", name):
		return frappe.get_doc("Project", name)
	return frappe.get_doc(
		{"doctype": "Project", "project_name": name, "company": company}
	).insert(ignore_permissions=True)


class TestProofofWork(FrappeTestCase):
	def setUp(self):
		self.company = _get_company()
		self.customer = _get_or_create_customer()

		# Project the contract and attendance both point to.
		self.project = _get_or_create_project(self.company)

		# The Contracts controller commits internally (breaking test rollback),
		# so build the fixture with a raw db_insert to keep the test isolated.
		self.contract = self._make_contract("_TEST-POW-CONTRACT-A")

		self.first_day = get_first_day(getdate(f"{TEST_YEAR}-{TEST_MONTH:02d}-01"))
		self.last_day = get_last_day(self.first_day)

		self._make_attendance()

	def _make_contract(self, name):
		"""Create an Active Contracts row via a raw insert.

		Bypasses the Contracts controller on purpose: it calls frappe.db.commit()
		in many code paths, which would commit test data and defeat the
		auto-rollback that keeps tests isolated.
		"""
		# Clear any leftover POWs for this contract so generation is not skipped.
		for pow_name in frappe.get_all(
			"Proof of Work", filters={"contract": name}, pluck="name"
		):
			frappe.db.delete("Proof of Work Item", {"parent": pow_name})
			frappe.db.delete("Proof of Work", {"name": pow_name})

		frappe.db.delete("Contracts", {"name": name})

		contract = frappe.new_doc("Contracts")
		contract.name = name
		contract.client = self.customer
		contract.project = self.project.name
		contract.price_list = frappe.db.get_value("Price List", {}, "name")
		contract.start_date = getdate(f"{TEST_YEAR}-01-01")
		contract.end_date = getdate(f"{TEST_YEAR}-12-31")
		contract.workflow_state = "Active"
		contract.db_insert()
		return contract

	def _make_attendance(self):
		"""Insert a bare attendance row (bypassing the heavy controller) for the project."""
		att_name = f"POW-TEST-ATT-{self.project.name}"
		# Idempotent: the Project fixture is persistent, so clear any leftover row
		# with this deterministic name before re-inserting.
		frappe.db.delete("Attendance", {"name": att_name})

		att = frappe.new_doc("Attendance")
		att.naming_series = "HR-ATT-.YYYY.-"
		att.employee = "_TEST-POW-EMP"
		att.status = "Present"
		att.working_hours = 8
		att.attendance_date = self.first_day
		att.company = self.company
		att.project = self.project.name
		att.docstatus = 1
		att.name = att_name
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
		# The base fixture has no contract line items and the attendance row has
		# no Sale Item (no Operations Role), so the summary table is empty:
		# a Proof of Work Item row is only created per resolvable Sale Item.
		self.assertEqual(len(pow_doc.proof_of_work_item), 0)

	# --- source hierarchy (AC1) -------------------------------------------------

	def _make_approved_amendment(self, workflow_state="Approved"):
		amendment = frappe.get_doc(
			{
				"doctype": "Attendance Amendment",
				"project": self.project.name,
				"year": str(TEST_YEAR),
				"month": "June",
				"attendance_based_on": "Attendance Status",
			}
		).insert(ignore_permissions=True)
		amendment.db_set("workflow_state", workflow_state)
		return amendment

	def test_source_falls_back_to_attendance_when_no_amendment(self):
		source_type, reference = resolve_attendance_source(
			self.contract.name, self.project.name, TEST_MONTH, TEST_YEAR
		)
		self.assertEqual(source_type, "attendance")
		self.assertIsNone(reference)

	def test_source_prefers_approved_amendment(self):
		amendment = self._make_approved_amendment()
		source_type, reference = resolve_attendance_source(
			self.contract.name, self.project.name, TEST_MONTH, TEST_YEAR
		)
		self.assertEqual(source_type, "amendment")
		self.assertEqual(reference, amendment.name)

	def test_source_ignores_unapproved_amendment(self):
		# A Pending Approval amendment must not be used as the source.
		self._make_approved_amendment(workflow_state="Pending Approval")
		source_type, reference = resolve_attendance_source(
			self.contract.name, self.project.name, TEST_MONTH, TEST_YEAR
		)
		self.assertEqual(source_type, "attendance")
		self.assertIsNone(reference)

	# --- contractual hours (shift hours from item code) ------------------------

	def test_shift_hours_parsed_from_item_code(self):
		# contractual_hours = planned days x these hours-per-shift.
		self.assertEqual(_shift_hours_from_item("SER-SEC-000136-NKW-M-30DY-12HR"), 12)
		self.assertEqual(_shift_hours_from_item("SER-SEC-000200-8HR"), 8)
		# Service items with no encoded hours -> 0 (contractual falls back to 0).
		self.assertEqual(_shift_hours_from_item("SER-FMG-001706"), 0)
		self.assertEqual(_shift_hours_from_item(""), 0)

	# --- read-only integrity (AC2) ---------------------------------------------

	def test_summary_fields_are_read_only(self):
		meta = frappe.get_meta("Proof of Work Item")
		for field in meta.fields:
			self.assertTrue(
				field.read_only,
				msg=f"Proof of Work Item field '{field.fieldname}' must be read-only",
			)

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
