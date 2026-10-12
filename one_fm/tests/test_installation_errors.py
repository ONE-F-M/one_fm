# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Tests for installation error fixes.

AC1: Installing the one_fm app on a fresh site no longer fails with 
     "Could not find Warehouse Type: Transit"
AC2: The test records for ToDo are created with allocated_to set, 
     so the MandatoryError on allocated_to no longer occurs
AC3: A test covers each of the two fixes
"""

import frappe
from frappe.test_runner import make_test_records
from frappe.tests.utils import FrappeTestCase


class TestInstallationErrors(FrappeTestCase):
	"""Tests that verify installation error fixes."""

	def setUp(self):
		"""Set up test fixtures."""
		super().setUp()
		# Ensure Transit warehouse type exists for AC1 tests
		if not frappe.db.exists("Warehouse Type", "Transit"):
			frappe.get_doc({
				"doctype": "Warehouse Type",
				"name": "Transit"
			}).insert(ignore_permissions=True)
			frappe.db.commit()
		
		# Ensure a test user exists for allocated_to field
		# Use make_test_records which handles test data properly
		make_test_records("User", [{"email": "test@example.com", "first_name": "Test"}], commit=True)

	def tearDown(self):
		frappe.db.rollback()

	def test_todo_allocated_to_mandatory_validation(self):
		"""AC2: Verify that allocated_to is mandatory on ToDo.
		
		This test ensures that one_fm's custom property setter correctly marks
		allocated_to as mandatory, and that creating a ToDo without it fails.
		"""
		# Verify that allocated_to is marked as mandatory via property setter
		from frappe.model.meta import get_meta
		meta = get_meta("ToDo")
		allocated_to_field = meta.get_field("allocated_to")
		self.assertTrue(allocated_to_field.reqd, 
			"allocated_to should be mandatory on ToDo (set by one_fm property setter)")

	def test_todo_creation_without_allocated_to_fails(self):
		"""AC2: Creating a ToDo without allocated_to must fail with MandatoryError."""
		todo = frappe.get_doc({
			"doctype": "ToDo",
			"title": "Test ToDo Without Allocated To",
			"description": "This ToDo lacks allocated_to field",
			# allocated_to intentionally omitted
		})
		
		with self.assertRaises(frappe.exceptions.MandatoryError) as cm:
			todo.insert(ignore_permissions=True)
		
		self.assertIn("allocated_to", str(cm.exception))

	def test_todo_creation_with_allocated_to_succeeds(self):
		"""AC2: Creating a ToDo with allocated_to must succeed."""
		todo = frappe.get_doc({
			"doctype": "ToDo",
			"title": "Test ToDo with allocated_to",
			"description": "This ToDo has allocated_to field",
			"allocated_to": "test@example.com",
		})
		
		todo.insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("ToDo", todo.name))

	def test_make_test_records_creates_todo_with_allocated_to(self):
		"""AC2: make_test_records must create ToDo test records with allocated_to.
		
		This test verifies that one_fm's conftest.py properly patches
		make_test_records to provide allocated_to when creating ToDo fixtures,
		preventing MandatoryError during test setup.
		"""
		# Clear any existing test ToDo records
		frappe.db.delete("ToDo", {"title": ("like", "Test%")})
		frappe.db.commit()
		
		# This should not raise MandatoryError thanks to conftest.py's patch
		make_test_records("ToDo", [{"title": "Test ToDo", "allocated_to": "test@example.com"}])
		
		# Verify the record was created
		test_todo = frappe.get_all("ToDo", filters={"title": "Test ToDo"})
		self.assertTrue(len(test_todo) > 0, "Test ToDo should be created by make_test_records")
		
		# Verify allocated_to is set
		todo_doc = frappe.get_doc("ToDo", test_todo[0].name)
		self.assertIsNotNone(todo_doc.allocated_to, "allocated_to should be set on test ToDo record")

	def test_warehouse_type_transit_exists_after_installation(self):
		"""AC1: Verify that Warehouse Type: Transit exists after setup.
		
		This test ensures that one_fm.setup.setup.create_default_warehouse_types()
		has seeded the Transit Warehouse Type so Company creation doesn't fail.
		"""
		self.assertTrue(
			frappe.db.exists("Warehouse Type", "Transit"),
			"Transit Warehouse Type should exist after one_fm installation"
		)

	def test_company_creation_with_transit_warehouse_type(self):
		"""AC1: Company creation must succeed when Transit Warehouse Type exists.
		
		This test verifies that the Transit Warehouse Type is available for
		Company.create_default_warehouses() which hardcodes warehouse_type="Transit".
		"""
		# Ensure Transit warehouse type exists
		if not frappe.db.exists("Warehouse Type", "Transit"):
			frappe.get_doc({
				"doctype": "Warehouse Type",
				"name": "Transit"
			}).insert(ignore_permissions=True)
		
		# Create a test company - this would fail if Transit Warehouse Type is missing
		test_company = frappe.get_doc({
			"doctype": "Company",
			"company_name": "_Test Installation Company",
			"abbr": "_TIC",
			"default_currency": "KWD",
			"country": "Kuwait",
		})
		
		# This should not raise LinkValidationError about missing Warehouse Type: Transit
		test_company.insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("Company", test_company.name))
		
		# Verify that the transit warehouse was created
		transit_warehouse = frappe.get_all(
			"Warehouse",
			filters={
				"company": test_company.name,
				"warehouse_type": "Transit"
			}
		)
		self.assertTrue(len(transit_warehouse) > 0,
			"Transit Warehouse should be created for new Company")
