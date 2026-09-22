# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-000446: a fresh site has no "Warehouse Type" "Transit" record until ERPNext's Setup
Wizard runs install_fixtures. Company.on_update() (erpnext/setup/doctype/company/company.py,
create_default_warehouses) always tries to insert a "Goods In Transit" Warehouse linked to
that Warehouse Type, so creating a Company outside the Setup Wizard flow (e.g. test record
setup on a fresh site) blows up with a LinkValidationError.

one_fm.patches.v15_0.seed_warehouse_type_transit.execute() is the fix: it seeds the
Warehouse Type idempotently, the same way add_pam_occupational_sectors seeds Occupational
Sector. It is also called from one_fm.setup.setup.after_install() so a fresh install is
covered without needing a migrate.
"""

import frappe
from frappe.exceptions import LinkValidationError
from frappe.tests.utils import FrappeTestCase

TEST_COMPANY = "WI-000446 Test Co"

# WI-000446 retry: re-touched to force a fresh test run in the sandbox.


def _delete_transit_warehouse_type():
	if frappe.db.exists("Warehouse Type", "Transit"):
		frappe.delete_doc("Warehouse Type", "Transit", force=True, ignore_permissions=True)


def _delete_test_company():
	if frappe.db.exists("Company", TEST_COMPANY):
		frappe.delete_doc("Company", TEST_COMPANY, force=True, ignore_permissions=True)


def _new_company_doc():
	return frappe.get_doc({
		"doctype": "Company",
		"company_name": TEST_COMPANY,
		"abbr": "WI446",
		"default_currency": "USD",
		"country": "United States",
	})


class TestCompanyCreationWarehouseType(FrappeTestCase):
	def setUp(self):
		_delete_test_company()

	def tearDown(self):
		_delete_test_company()

	def test_company_creation_fails_without_transit_warehouse_type(self):
		"""WI-000446 reproduction: with Warehouse Type "Transit" absent (as on a fresh
		site that never ran the Setup Wizard), creating a Company raises
		LinkValidationError from erpnext's create_default_warehouses()."""
		_delete_transit_warehouse_type()

		company = _new_company_doc()
		with self.assertRaises(LinkValidationError):
			company.insert(ignore_permissions=True)
