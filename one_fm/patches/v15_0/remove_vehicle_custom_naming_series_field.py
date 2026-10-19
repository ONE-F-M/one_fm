import frappe


def execute():
	"""Remove the obsolete custom_naming_series Custom Field from Vehicle.

	Vehicle naming now uses the standard `naming_series` field (autoname
	"naming_series:"), so the earlier custom_naming_series field is no longer
	needed. Delete the Custom Field and drop its column if it exists.
	"""
	if frappe.db.exists("Custom Field", {"dt": "Vehicle", "fieldname": "custom_naming_series"}):
		frappe.db.delete("Custom Field", {
			"dt": "Vehicle",
			"fieldname": "custom_naming_series",
		})

		# Drop the column from the table if it was already synced
		if frappe.db.has_column("Vehicle", "custom_naming_series"):
			frappe.db.sql_ddl("ALTER TABLE `tabVehicle` DROP COLUMN `custom_naming_series`")

		frappe.clear_cache(doctype="Vehicle")
		frappe.db.commit()
