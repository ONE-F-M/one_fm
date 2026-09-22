# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""Regression test for WI-000447.

ERPNext's Company.create_default_warehouses() hardcodes
warehouse_type="Transit" when creating the default warehouses for a new
Company. The "Warehouse Type: Transit" record is normally seeded only by
ERPNext's interactive Setup Wizard (install_fixtures.install()), which
one_fm's own install/migrate flow never runs. On a fresh one_fm install (or
any site where that record was never seeded), creating a Company therefore
fails with:

    frappe.exceptions.LinkValidationError: Could not find Warehouse Type: Transit

one_fm.setup.setup.create_default_warehouse_types() seeds that record so
fresh installs (via after_install) and existing sites (via the
add_transit_warehouse_type patch) both have it before a Company is ever
created.
"""

import frappe
from frappe.tests.utils import FrappeTestCase


def _delete_transit_warehouse_type_if_present():
	if frappe.db.exists("Warehouse Type", "Transit"):
		frappe.delete_doc("Warehouse Type", "Transit", force=True, ignore_permissions=True)
		frappe.db.commit()


def _new_test_company(abbr):
	return frappe.get_doc(
		{
			"doctype": "Company",
			"company_name": f"_Test Transit WT Company {abbr}",
			"abbr": abbr,
			"default_currency": "KWD",
			"country": "Kuwait",
		}
	)


class TestDefaultWarehouseTypeTransit(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_company_creation_fails_without_warehouse_type_transit(self):
		"""Reproduces the bug: with the Transit Warehouse Type absent, Company
		creation must fail with LinkValidationError, exactly as reported."""
		_delete_transit_warehouse_type_if_present()

		company = _new_test_company("_TWT1")
		with self.assertRaises(frappe.exceptions.LinkValidationError) as cm:
			company.insert(ignore_permissions=True)

		self.assertIn("Warehouse Type", str(cm.exception))
		self.assertIn("Transit", str(cm.exception))

	def test_create_default_warehouse_types_fixes_company_creation(self):
		"""Once the seeding fix runs (as it does from after_install on a fresh
		install, and from the migrate-time patch on an existing site), Company
		creation must succeed and the Warehouse Type must exist."""
		_delete_transit_warehouse_type_if_present()

		from one_fm.setup.setup import create_default_warehouse_types

		create_default_warehouse_types()

		self.assertTrue(frappe.db.exists("Warehouse Type", "Transit"))

		company = _new_test_company("_TWT2")
		company.insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("Company", company.name))
