# -*- coding: utf-8 -*-
# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class DocumentRequest(Document):
	def validate(self):
		self.set_requester_defaults()
		self.check_approver_resolved()
		self.apply_reference_document_defaults()

	def set_requester_defaults(self):
		if not self.requester:
			employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
			if employee:
				self.requester = employee

	def check_approver_resolved(self):
		if self.requester and not self.approver:
			frappe.throw(
				_(
					"Could not resolve an approver for {0} — their Employee record has no "
					"'Reports To' (line manager) set. Set it on the Employee record first."
				).format(self.requester)
			)

	def apply_reference_document_defaults(self):
		if self.request_action == "Create" or not self.reference_document:
			return
		ref = frappe.db.get_value(
			"AI Reference Index", self.reference_document, ["document_type", "title"], as_dict=True
		)
		if not ref:
			return
		self.document_type = ref.document_type
		if not self.title:
			self.title = ref.title


# ── Reaching the published document ─────────────────────────────────────────
# `document_link` holds the Google Docs URL, and it is the only thing the form
# reads. A stored field beats resolving on every view: it renders without a
# server round-trip, and it shows up in list view, reports and exports, which a
# computed value never would.
#
# The process writes it at publish. Everything below exists to populate it when
# the process did not — which covers every document published before the field
# existed, and any run whose publish step predates the map change that writes
# it. Two sources, in order of authority:
#
#   1. AI Reference Index.drive_file_link — written by the map's "Drive — Index
#      Document" step at publish. This is the canonical record of the published
#      document, and `reference_document` already links to it. It is only
#      populated for Update/Delete requests, where the user picks it up front;
#      a Create request publishes without ever being pointed at the entry its
#      own run created.
#
#   2. The BPMN instance's task data — `drive_file.webViewLink`, the value the
#      Drive connector returned when the file was made.
#
# Resolution is therefore a repair path, not the read path. It fills the field
# the first time anyone looks, so each request pays it once rather than on
# every view.

# Statuses where there is no document to open, even though the request may
# still name one. "Deleted" is the case that matters: a Delete request points
# at the document it removed.
NO_DOCUMENT_STATUSES = ("Deleted", "Request Rejected")


@frappe.whitelist()
def get_published_document_link(document_request: str) -> dict:
	"""Return the Google Docs link for a published Document Request.

	Returns ``{"url": ..., "title": ..., "source": ...}``, or ``{}`` when no
	link can be found — an unpublished request, or a published one whose run
	predates the Drive integration. ``source`` says which of the two routes
	answered, so a support question can be diagnosed from the response alone.
	"""
	if not frappe.has_permission("Document Request", "read", doc=document_request):
		frappe.throw(_("Not permitted to read this Document Request."), frappe.PermissionError)

	request = frappe.db.get_value(
		"Document Request",
		document_request,
		["name", "title", "status", "reference_document", "document_link"],
		as_dict=True,
	)
	if not request:
		return {}

	# A completed Delete request still carries a reference_document — the user
	# picked it in order to say what to delete. Resolving it would hand back a
	# link to a file that the process has since removed from Drive.
	if request.status in NO_DOCUMENT_STATUSES:
		return {}

	# The stored field is the answer whenever it is set — no lookups at all.
	if request.document_link:
		return {
			"url": request.document_link,
			"title": request.title,
			"source": "document_link",
		}

	# 1. The canonical index entry, when the request is pointed at one.
	source = url = None
	title = request.title
	if request.reference_document:
		entry = frappe.db.get_value(
			"AI Reference Index",
			request.reference_document,
			["drive_file_link", "title"],
			as_dict=True,
		)
		if entry and entry.drive_file_link:
			url, title, source = entry.drive_file_link, entry.title or request.title, "reference_document"

	# 2. The run that produced it. `update_field` writes status with
	#    frappe.db.set_value, so no doc hook fires at publish — for any run
	#    predating the map change, the instance is the only remaining record of
	#    what was created.
	if not url:
		url = _link_from_process_instance(document_request)
		source = "process_instance" if url else None

	if not url:
		return {}

	_remember(document_request, url)
	return {"url": url, "title": title, "source": source}


def _remember(document_request: str, url: str) -> None:
	"""Store a repaired link so this resolution happens once, not per view.

	Written straight to the database: the field is read-only and derived, so it
	must not bump ``modified`` or add a Version row — a stale-document error on
	someone else's open form would be a poor trade for a cached URL. A failure
	here is not worth failing the read over; the caller still gets its link.
	"""
	try:
		frappe.db.set_value(
			"Document Request", document_request, "document_link", url, update_modified=False
		)
	except Exception:
		frappe.log_error(
			title="Document Request: could not store the resolved document link",
			message=frappe.get_traceback(),
		)


def _link_from_process_instance(document_request: str) -> str | None:
	"""Dig the Drive webViewLink out of the run's serialised task data."""
	instance = frappe.db.get_value(
		"BPMN Process Instance",
		{"context_doctype": "Document Request", "context_docname": document_request},
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
	if not isinstance(drive_file, dict):
		return None

	# webViewLink is what Drive returns; build one from the id if it is absent
	# (older runs recorded the id alone).
	link = drive_file.get("webViewLink")
	if link:
		return link
	file_id = drive_file.get("id")
	return f"https://docs.google.com/document/d/{file_id}/edit" if file_id else None
