import frappe


def execute():
	"""Remove old 'Fleet' workspace record so the new 'Transportation' standard
	workspace loads cleanly on bench migrate. Also remove any stale
	'Transportation' record to avoid duplicate conflicts."""

	for ws_name in ("Fleet", "Transportation", "Rambo"):
		if frappe.db.exists("Workspace", ws_name):
			frappe.delete_doc("Workspace", ws_name, force=True, ignore_permissions=True)

	frappe.clear_cache()
