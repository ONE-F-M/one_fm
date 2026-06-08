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

	# Step 2: Sync the naming series counter so it continues from the highest existing name
	max_name = frappe.db.sql("""
		SELECT name FROM `tabVehicle`
		WHERE name LIKE 'VHL-%%'
		ORDER BY LENGTH(name) DESC, name DESC
		LIMIT 1
	""")

	if max_name:
		# Extract the numeric part (e.g., "VHL-0042" → 42)
		current = max_name[0][0]
		try:
			num = int(current.split("-", 1)[1])
		except (IndexError, ValueError):
			num = 0

		# Update or insert the Series record so getseries() continues from here
		if frappe.db.exists("Series", "VHL-"):
			frappe.db.sql("UPDATE `tabSeries` SET current = %s WHERE name = %s", (num, "VHL-"))
		else:
			frappe.db.sql("INSERT INTO `tabSeries` (name, current) VALUES (%s, %s)", ("VHL-", num))

	frappe.db.commit()
