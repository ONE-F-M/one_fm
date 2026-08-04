# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""
Point published Document Requests at the Document Register entry they created.

A Create request publishes a Google Doc and the map indexes it as an
``Document Register`` entry — but nothing writes that entry back onto the
request. ``Document Request.reference_document`` already links to exactly this
doctype; it is simply only ever filled in by the user, on Update and Delete
requests, and never by the run itself.

The consequence is that a published request holds no route to the document it
produced. ``get_published_document_link`` can still find it by reading the
run's serialised task data, but that is a fallback, not a fix: it depends on
the instance surviving and on the internal shape of the task data.

This patch closes the gap for requests already published, by matching each one
to the index entry its own run recorded.
"""

import frappe


def execute():
	published = frappe.get_all("Document Request", filters={"status": "Published"}, pluck="name")
	if not published:
		return

	linked = filled = 0
	for request in published:
		entry = _index_entry_for(request)
		# Only link to an entry that actually exists — the file id is the index
		# entry's primary key, so a run whose document was later deleted from
		# Drive would otherwise leave a dangling Link.
		if entry and frappe.db.exists("Document Register", entry):
			if not frappe.db.get_value("Document Request", request, "reference_document"):
				frappe.db.set_value(
					"Document Request", request, "reference_document", entry, update_modified=False
				)
				linked += 1

		# document_link is what the form actually reads. Resolve it the same way
		# a form view would, so the field is populated up front instead of being
		# repaired one request at a time as people open them.
		if not frappe.db.get_value("Document Request", request, "document_link"):
			from one_fm.one_fm.doctype.document_request.document_request import (
				get_published_document_link,
			)

			if get_published_document_link(request).get("url"):
				filled += 1

	frappe.db.commit()
	print(
		f"{len(published)} published Document Request(s): "
		f"{linked} linked to an index entry, {filled} document_link(s) filled"
	)


def _index_entry_for(request: str) -> str | None:
	"""The Drive file id recorded by the run — which is the index entry's name.

	Matching on the file id rather than on title keeps this correct when two
	requests produced documents with the same title, which is the normal case
	for a re-run.
	"""
	instance = frappe.db.get_value(
		"BPMN Process Instance",
		{"context_doctype": "Document Request", "context_docname": request},
		"name",
		order_by="creation desc",
	)
	if not instance:
		return None

	try:
		state = frappe.parse_json(
			frappe.db.get_value("BPMN Process Instance", instance, "workflow_state") or "{}"
		)
	except Exception:
		return None

	drive_file = (state.get("data") or {}).get("drive_file") or {}
	return drive_file.get("id") if isinstance(drive_file, dict) else None
