import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from one_fm.custom.custom_field.vehicle import get_vehicle_custom_fields


def execute():
	"""
	1. Apply updated Vehicle custom fields (adds Subcontractor option to
	   one_fm_vehicle_category and creates the hidden custom_naming_series field).
	2. Initialise the VHL-L- Series counter for Leased vehicles.
	3. Back-fill custom_naming_series on existing Vehicle records so the
	   hidden field accurately reflects each vehicle's naming prefix.
	"""
	# 1. Apply custom field definitions
	create_custom_fields(get_vehicle_custom_fields(), update=True)

	# 2. Ensure the VHL-L- series counter exists for Leased vehicles
	#    (VHL-S- already exists from the earlier remove_vehicle_autoname_property_setter patch)
	max_leased = frappe.db.sql("""
		SELECT MAX(CAST(SUBSTRING_INDEX(name, '-', -1) AS UNSIGNED))
		FROM `tabVehicle`
		WHERE name REGEXP '^VHL-L-[0-9]+$'
	""")

	num = max_leased[0][0] if max_leased and max_leased[0][0] else 0

	if frappe.db.exists("Series", "VHL-L-"):
		frappe.db.sql("UPDATE `tabSeries` SET current = %s WHERE name = %s", (num, "VHL-L-"))
	else:
		frappe.db.sql("INSERT INTO `tabSeries` (name, current) VALUES (%s, %s)", ("VHL-L-", num))

	# 3. Back-fill custom_naming_series on existing records
	series_map = {
		"Owned": "VHL-.####",
		"Leased": "VHL-L-.####",
		"Subcontractor": "VHL-S-.####",
	}

	for category, series in series_map.items():
		frappe.db.sql(
			"""
			UPDATE `tabVehicle`
			SET custom_naming_series = %s
			WHERE one_fm_vehicle_category = %s
			  AND (custom_naming_series IS NULL OR custom_naming_series = '')
			""",
			(series, category),
		)

	# Default fallback for records with no category set
	frappe.db.sql(
		"""
		UPDATE `tabVehicle`
		SET custom_naming_series = 'VHL-.####'
		WHERE (one_fm_vehicle_category IS NULL OR one_fm_vehicle_category = '')
		  AND (custom_naming_series IS NULL OR custom_naming_series = '')
		"""
	)

	frappe.db.commit()
	frappe.clear_cache(doctype="Vehicle")
