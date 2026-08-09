# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""
Give every already-registered document a version history and a lifecycle state.

Versioning starts counting at the next publish, which leaves documents already
in the register looking like they have no history at all — ``current_version``
0, no ``Document Revision`` row, and a blank lifecycle that reads as neither
active nor withdrawn. This patch states what is already true about them: each
one is at version 1, and that version's text is whatever the register holds.

Two wrinkles it has to absorb:

1. ``content`` is empty on every row published since 2026-07-29. The map's
   "Drive — Index Document" step was reading ``sop_markdown``, a variable the
   Document Request unification renamed to ``document_markdown``, so the field
   was written as an empty string on every run. The fix ships with this work,
   but it cannot retroactively fill rows already written — so the snapshot is
   recovered by downloading the document's text from Drive.

2. The old Delete branch trashed the Drive file. Those documents are withdrawn
   in fact, so they are recorded as ``Inactive`` here, and their download may
   fail because the file is in the Drive trash. A missing snapshot is worth
   less than a failed migration: the download is attempted, and a failure
   leaves ``content_snapshot`` empty rather than aborting.
"""

import frappe
from frappe.utils import cint


def execute():
	frappe.reload_doc("one_fm", "doctype", "document_revision")
	frappe.reload_doc("one_fm", "doctype", "document_register")
	frappe.reload_doc("one_fm", "doctype", "document_request")

	entries = frappe.get_all(
		"Document Register",
		fields=["name", "title", "document_type", "drive_file_link", "content", "current_version"],
	)
	if not entries:
		print("No Document Register entries to seed.")
		return

	withdrawn = _withdrawn_documents()
	coded = versioned = downloaded = inactive = 0

	for entry in entries:
		code = _ensure_code(entry)
		if code:
			coded += 1

		state = "Inactive" if entry.name in withdrawn else "Active"
		if state == "Inactive":
			inactive += 1

		updates = {"lifecycle_state": state}
		if state == "Inactive":
			# Attribute it to the request that did it, so the register explains
			# itself without anyone having to correlate timestamps by hand.
			request = withdrawn[entry.name]
			updates["deactivated_via_request"] = request.get("name")
			updates["deactivation_reason"] = request.get("requirement_text") or (
				"Withdrawn by request {0} before versioning existed.".format(request.get("name"))
			)
			updates["deactivated_on"] = request.get("modified")
			updates["deactivated_by"] = request.get("owner")

		if not cint(entry.current_version):
			updates["current_version"] = 1

		frappe.db.set_value("Document Register", entry.name, updates, update_modified=False)

		if _has_version_row(entry.name):
			continue

		snapshot = entry.content or ""
		if not snapshot:
			snapshot = _text_from_drive(entry.name)
			if snapshot:
				downloaded += 1

		_create_version_row(entry, code, snapshot, withdrawn.get(entry.name))
		versioned += 1

	frappe.db.commit()
	print(
		f"{len(entries)} document(s) seeded: {coded} coded, {versioned} v1 record(s) created, "
		f"{downloaded} snapshot(s) recovered from Drive, {inactive} marked Inactive"
	)


def _ensure_code(entry) -> str | None:
	"""Allocate a readable document code, keeping any that is already set."""
	existing = frappe.db.get_value("Document Register", entry.name, "document_code")
	if existing:
		return existing

	from one_fm.one_fm.doctype.document_register.document_register import allocate_document_code

	code = allocate_document_code(entry.document_type)
	frappe.db.set_value("Document Register", entry.name, "document_code", code, update_modified=False)
	return code


def _withdrawn_documents() -> dict:
	"""Documents a completed Delete request already took out of use.

	Keyed by index entry, valued by the request that withdrew it. Only completed
	Delete requests count — a rejected or in-flight one withdrew nothing.
	"""
	requests = frappe.get_all(
		"Document Request",
		filters={"request_action": "Delete", "status": "Deleted"},
		fields=["name", "reference_document", "requirement_text", "modified", "owner"],
		order_by="modified asc",
	)
	return {r.reference_document: r for r in requests if r.reference_document}


def _has_version_row(document: str) -> bool:
	return bool(frappe.db.exists("Document Revision", {"document": document}))


def _text_from_drive(file_id: str) -> str:
	"""Recover a document's text from Drive, or return "" if it cannot be read.

	A trashed file is often still readable through the API, so this is worth
	attempting even for the withdrawn documents — but it is a best effort, and
	the migration must not depend on Drive being reachable at all.
	"""
	try:
		from one_bpmn.one_bpmn.integrations.google_drive import download_file_text

		return download_file_text(file_id) or ""
	except Exception:
		frappe.log_error(
			title=f"seed_document_versions: could not read {file_id} from Drive",
			message=frappe.get_traceback(),
		)
		return ""


def _create_version_row(entry, code: str, snapshot: str, request) -> None:
	"""Record the existing document as version 1.

	``published_on`` is the entry's own creation date rather than now: the
	document was published when it was published, and stamping the migration
	date would make the register lie about when it took effect.
	"""
	created = frappe.db.get_value("Document Register", entry.name, "creation")
	owner = frappe.db.get_value("Document Register", entry.name, "owner")

	version = frappe.get_doc(
		{
			"doctype": "Document Revision",
			"document": entry.name,
			"document_code": code,
			"version": 1,
			"title_at_version": entry.title,
			"document_type": entry.document_type,
			"drive_file_link": entry.drive_file_link,
			"content_snapshot": snapshot,
			"published_on": created,
			"published_by": owner,
			"change_reason": "Initial version, recorded when document versioning was introduced.",
			"document_request": _creating_request(entry.name),
		}
	)
	version.insert(ignore_permissions=True)


def _creating_request(document: str) -> str | None:
	"""The Create request that produced this document, if one is on record."""
	return frappe.db.get_value(
		"Document Request",
		{"reference_document": document, "request_action": "Create", "status": "Published"},
		"name",
		order_by="creation asc",
	)
