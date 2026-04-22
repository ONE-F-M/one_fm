import frappe


def execute():
	"""Drop the legacy 'type' column from Pathfinder Log."""
	if frappe.db.has_column("Pathfinder Log", "type"):
		frappe.db.sql("ALTER TABLE `tabPathfinder Log` DROP COLUMN `type`")
	frappe.db.commit()
