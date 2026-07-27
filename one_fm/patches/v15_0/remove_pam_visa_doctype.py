import frappe


def execute():
	"""Remove the deprecated PAM Visa DocType (superseded by Visa Request)."""
	if not frappe.db.exists("DocType", "PAM Visa"):
		return

	# Drop the DocType and its table. force=1 skips the linked-document check:
	# the Visa Stamping link field and the Candidate Country Process dashboard
	# link are removed in the same release via schema/source changes, and this
	# patch runs in post_model_sync (after those changes are applied).
	frappe.delete_doc("DocType", "PAM Visa", force=1, ignore_permissions=True)

	# Clean up any metadata rows that still referenced the deleted DocType.
	frappe.db.delete("Custom Field", {"dt": "PAM Visa"})
	frappe.db.delete("Property Setter", {"doc_type": "PAM Visa"})
	frappe.db.delete("DocType Link", {"link_doctype": "PAM Visa"})

	frappe.db.commit()
