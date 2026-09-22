import frappe

# WI-000446: a fresh site has no "Warehouse Type" "Transit" record until ERPNext's Setup
# Wizard runs install_fixtures. Company.on_update() (erpnext/setup/doctype/company/company.py,
# create_default_warehouses) always tries to insert a "Goods In Transit" Warehouse linked to
# that Warehouse Type, so creating a Company outside the Setup Wizard flow (e.g. a fresh
# install/migrate, or test record setup) blows up with a LinkValidationError. Seed it
# idempotently, the same way add_pam_occupational_sectors seeds Occupational Sector.

WAREHOUSE_TYPE = "Transit"


def execute():
	create_warehouse_type_transit()
	verify()


def create_warehouse_type_transit():
	if not frappe.db.exists("Warehouse Type", WAREHOUSE_TYPE):
		frappe.get_doc({
			"doctype": "Warehouse Type",
			"name": WAREHOUSE_TYPE,
		}).insert(ignore_permissions=True)


def verify():
	if not frappe.db.exists("Warehouse Type", WAREHOUSE_TYPE):
		frappe.throw(
			f"WI-000446: Warehouse Type '{WAREHOUSE_TYPE}' was not created. Company.on_update() "
			"(erpnext create_default_warehouses) links a Warehouse to this Warehouse Type, so "
			"creating a Company without it raises LinkValidationError."
		)
