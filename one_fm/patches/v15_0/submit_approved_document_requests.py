import frappe


def execute():
	"""Submit the Document Requests that are Approved but still Draft, so they lock against edits."""
	frappe.reload_doc("one_fm", "doctype", "document_request")
	if not frappe.db.has_column("Document Request", "workflow_state"):
		return

	frappe.db.set_value(
		"Document Request",
		{"workflow_state": "Approved", "docstatus": 0},
		"docstatus",
		1,
		update_modified=False,
	)
