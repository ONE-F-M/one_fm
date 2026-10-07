import frappe


def execute():
	"""Drop the approver column from Document Request."""
	if frappe.db.has_column("Document Request", "approver"):
		frappe.db.sql_ddl("ALTER TABLE `tabDocument Request` DROP COLUMN `approver`")

	frappe.db.delete("Property Setter", {"doc_type": "Document Request", "field_name": "approver"})
	frappe.clear_cache(doctype="Document Request")
