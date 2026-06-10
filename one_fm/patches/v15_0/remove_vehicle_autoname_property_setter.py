import frappe


def execute():
	"""Remove the static Vehicle autoname Property Setter and the obsolete
	custom_naming_series Custom Field so the new autoname doc_event hook
	(vehicle_autoname) takes effect.

	Also initialise the VHL-S- Series counter so Leased vehicles start from
	the correct sequence number.
	"""
	# 1. Delete Property Setter that sets autoname on Vehicle
	#    (created by the earlier patch update_vehicle_naming_series and/or
	#     the app-level property setter in custom/property_setter/vehicle.py)
	frappe.db.delete("Property Setter", {
		"doc_type": "Vehicle",
		"property": "autoname",
	})

	# 2. Delete the UI-created custom_naming_series Custom Field (if it exists)
	if frappe.db.exists("Custom Field", {"dt": "Vehicle", "fieldname": "custom_naming_series"}):
		frappe.db.delete("Custom Field", {
			"dt": "Vehicle",
			"fieldname": "custom_naming_series",
		})

		# Drop the column from the table if it was already synced
		if frappe.db.has_column("Vehicle", "custom_naming_series"):
			frappe.db.sql_ddl("ALTER TABLE `tabVehicle` DROP COLUMN `custom_naming_series`")

	# 3. Ensure the VHL-S- Series counter exists for Leased vehicles
	#    so getseries() can continue from the highest existing name.
	max_leased = frappe.db.sql("""
		SELECT MAX(CAST(SUBSTRING(name, 7) AS UNSIGNED))
		FROM `tabVehicle`
		WHERE name REGEXP '^VHL-S-[0-9]+$'
	""")

	num = max_leased[0][0] if max_leased and max_leased[0][0] else 0

	if frappe.db.exists("Series", "VHL-S-"):
		frappe.db.sql("UPDATE `tabSeries` SET current = %s WHERE name = %s", (num, "VHL-S-"))
	else:
		frappe.db.sql("INSERT INTO `tabSeries` (name, current) VALUES (%s, %s)", ("VHL-S-", num))

	frappe.db.commit()
	frappe.clear_cache(doctype="Vehicle")
