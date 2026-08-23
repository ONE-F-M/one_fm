import frappe

from one_fm.grd.doctype.preparation.preparation import SUB_DOCUMENT_SEQUENCE

# WI-002093: the row now shows which sub-document the candidate has reached instead of what
# the row costs. Existing rows have never had it filled in, so it is backfilled once - the
# handler that keeps it current only fires when a sub-document is saved.


def execute():
	frappe.reload_doc("grd", "doctype", "preparation_record")

	for doctype in SUB_DOCUMENT_SEQUENCE:
		backfill(doctype)


def backfill(doctype):
	"""Point every row at this doctype's document, in sequence order.

	Run in the sequence's own order so the later documents overwrite the earlier ones and
	each row ends up on the furthest it has reached - the same rule the handler applies.
	"""
	documents = frappe.get_all(
		doctype,
		filters={"preparation": ["is", "set"], "docstatus": ["<", 2]},
		fields=["name", "preparation", "employee", "workflow_state"],
	)
	for document in documents:
		row = frappe.db.get_value(
			"Preparation Record",
			{
				"parent": document.preparation,
				"parenttype": "Preparation",
				"employee": document.employee,
			},
			"name",
		)
		if not row:
			continue

		frappe.db.set_value(
			"Preparation Record",
			row,
			{
				"ref_doctype": doctype,
				"ref_name": document.name,
				"ref_doctype_status": document.workflow_state or "",
			},
			update_modified=False,
		)
