# Copyright (c) 2026, ONE FM and contributors
# See license.txt
"""WI-000447: seed the "Transit" Warehouse Type for existing sites that only
migrate rather than fresh-install, mirroring
one_fm.setup.setup.create_default_warehouse_types() which covers fresh
installs via after_install.

ERPNext's Company.create_default_warehouses() hardcodes
warehouse_type="Transit" when creating the default warehouses for a new
Company. That "Warehouse Type" record is normally seeded only by ERPNext's
interactive Setup Wizard (install_fixtures.install()), which one_fm's
install/migrate flow never runs, so Company creation fails with:
	LinkValidationError: Could not find Warehouse Type: Transit
"""

from one_fm.setup.setup import create_default_warehouse_types


def execute():
	create_default_warehouse_types()
