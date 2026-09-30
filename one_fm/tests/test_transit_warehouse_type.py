# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Regression test for WI-000423.

On a fresh one_fm install created outside the interactive Setup Wizard flow
(e.g. `bench make_test_records`), the "Transit" Warehouse Type record does not
exist. ERPNext's Company.on_update() calls create_default_warehouses(), which
creates a "Goods In Transit" warehouse with warehouse_type="Transit", and
without that Warehouse Type record Company creation used to fail with:

	frappe.exceptions.LinkValidationError: Could not find Warehouse Type: Transit

one_fm.setup.setup.ensure_transit_warehouse_type() seeds that record, and is
wired as a Company before_insert hook so it runs before any Company is ever
created, wizard or not.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from one_fm.setup.setup import ensure_transit_warehouse_type

TEST_COMPANY_NAME = "WI-000423 Test Transit Co"


class TestEnsureTransitWarehouseType(FrappeTestCase):
	def setUp(self):
		# Reproduce the fresh-install condition: the Transit Warehouse Type
		# does not exist yet.
		frappe.db.delete("Warehouse Type", {"name": "Transit"})
		frappe.db.commit()

	def tearDown(self):
		frappe.db.delete("Company", {"name": TEST_COMPANY_NAME})
		frappe.db.commit()

	def test_transit_warehouse_type_is_missing_before_the_fix_runs(self):
		self.assertFalse(frappe.db.exists("Warehouse Type", "Transit"))

	def test_ensure_transit_warehouse_type_creates_the_record(self):
		ensure_transit_warehouse_type()
		self.assertTrue(frappe.db.exists("Warehouse Type", "Transit"))

	def test_ensure_transit_warehouse_type_is_idempotent(self):
		ensure_transit_warehouse_type()
		# calling it again with the record already present must not raise
		ensure_transit_warehouse_type()
		self.assertTrue(frappe.db.exists("Warehouse Type", "Transit"))

	def test_company_creation_no_longer_raises_link_validation_error(self):
		"""Reproduces the reported failure scenario: create a Company with the
		Transit Warehouse Type missing, exactly as would happen on a fresh
		install outside the Setup Wizard. Before the fix this raised
		frappe.exceptions.LinkValidationError on Company.on_update()'s
		create_default_warehouses() call."""
		self.assertFalse(frappe.db.exists("Warehouse Type", "Transit"))

		company = frappe.get_doc({
			"doctype": "Company",
			"company_name": TEST_COMPANY_NAME,
			"abbr": "W423",
			"default_currency": "USD",
			"country": "United States",
		})
		# Must not raise frappe.exceptions.LinkValidationError.
		company.insert(ignore_permissions=True)

		self.assertTrue(frappe.db.exists("Company", TEST_COMPANY_NAME))
		self.assertTrue(frappe.db.exists("Warehouse Type", "Transit"))

	def test_company_before_insert_hook_is_registered(self):
		hooks = frappe.get_hooks("doc_events").get("Company", {})
		before_insert = hooks.get("before_insert") or []
		if isinstance(before_insert, str):
			before_insert = [before_insert]
		self.assertIn("one_fm.setup.setup.ensure_transit_warehouse_type", before_insert)
