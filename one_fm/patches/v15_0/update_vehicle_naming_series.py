import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def execute():
	# Step 1: Apply the autoname property setter
	make_property_setter(
		doctype="Vehicle",
		fieldname=None,
		property="autoname",
		value="VHL-.####",
		property_type="Data",
		for_doctype=True,
		validate_fields_for_doctype=False,
	)

	# Step 2: Sync the naming series counter so it continues from the highest existing name.
	# Filter to names with purely numeric suffixes to avoid irregular names (e.g. VHL-TEST)
	# resetting the counter and causing collisions.
	max_counter = frappe.db.sql("""
		SELECT MAX(CAST(SUBSTRING(name, 5) AS UNSIGNED))
		FROM `tabVehicle`
		WHERE name REGEXP '^VHL-[0-9]+$'
	""")

	num = max_counter[0][0] if max_counter and max_counter[0][0] else 0

	# Update or insert the Series record so getseries() continues from here
	if frappe.db.exists("Series", "VHL-"):
		frappe.db.sql("UPDATE `tabSeries` SET current = %s WHERE name = %s", (num, "VHL-"))
	else:
		frappe.db.sql("INSERT INTO `tabSeries` (name, current) VALUES (%s, %s)", ("VHL-", num))

	frappe.db.commit()
