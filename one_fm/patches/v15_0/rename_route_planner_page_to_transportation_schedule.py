import frappe


def execute():
	"""Remove the old 'route-planner' Page record so the new
	'transportation-schedule' standard page loads cleanly on bench migrate."""

	if frappe.db.exists("Page", "route-planner"):
		frappe.delete_doc("Page", "route-planner", force=True, ignore_permissions=True)

	frappe.clear_cache()
