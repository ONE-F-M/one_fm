from collections import Counter

import frappe

DOCUMENT_TYPES = ("Policy", "SOP", "Guideline", "Manual", "Knowledge Base")


def execute():
	"""Create a DMS Document Type per type, then set open Create requests to their type's guideline."""
	for document_type in DOCUMENT_TYPES:
		if not frappe.db.exists("DMS Document Type", document_type):
			frappe.get_doc(
				{
					"doctype": "DMS Document Type",
					"document_type_name": document_type,
					"source_guideline": _most_used_guideline(document_type),
				}
			).insert(ignore_permissions=True)

	for request in frappe.get_all(
		"Document Request",
		filters={"request_action": "Create", "workflow_state": ["!=", "Approved"]},
		fields=["name", "document_type", "source_guideline"],
	):
		guideline = frappe.db.get_value("DMS Document Type", request.document_type, "source_guideline")
		if guideline and guideline != request.source_guideline:
			frappe.db.set_value(
				"Document Request", request.name, "source_guideline", guideline, update_modified=False
			)


def _most_used_guideline(document_type: str) -> str | None:
	"""The active Guideline that this type's Create requests have used most, or None."""
	used = frappe.get_all(
		"Document Request",
		filters={
			"request_action": "Create",
			"document_type": document_type,
			"source_guideline": ["is", "set"],
		},
		pluck="source_guideline",
	)
	for guideline, _count in Counter(used).most_common():
		if frappe.db.get_value("Document Register", guideline, ["document_type", "lifecycle_state"]) == (
			"Guideline",
			"Active",
		):
			return guideline
	return None
