import frappe


def execute():
	"""Backfill governorate_area and governorate for existing Site To Location Mapping rows."""

	# Build a map of Location -> governorate_area
	locations = frappe.get_all(
		"Location",
		filters={"governorate_area": ["is", "set"]},
		fields=["name", "governorate_area"],
	)
	location_to_area = {loc.name: loc.governorate_area for loc in locations}

	# Build a map of Governorate Area -> governorate
	areas = frappe.get_all(
		"Governorate Area",
		filters={"governorate": ["is", "set"]},
		fields=["name", "governorate"],
	)
	area_to_gov = {area.name: area.governorate for area in areas}

	# Get all child rows that need updating
	rows = frappe.get_all(
		"Site To Location Mapping",
		filters={"location": ["is", "set"]},
		fields=["name", "location", "governorate_area", "governorate"],
	)

	updated = 0
	for row in rows:
		gov_area = location_to_area.get(row.location)
		gov = area_to_gov.get(gov_area) if gov_area else None

		updates = {}
		if gov_area and row.governorate_area != gov_area:
			updates["governorate_area"] = gov_area
		if gov and row.governorate != gov:
			updates["governorate"] = gov

		if updates:
			frappe.db.set_value("Site To Location Mapping", row.name, updates, update_modified=False)
			updated += 1

	if updated:
		frappe.db.commit()

	frappe.msgprint(f"Updated {updated} of {len(rows)} rows.")
