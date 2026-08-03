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
# Once the process publishes, the Google Doc exists and is readable — but the
# request that produced it holds no way to reach it. The link is recorded in
# two places and neither is on this form:
#
#   1. AI Reference Index.drive_file_link — written by the map's "Drive — Index
#      Document" step at publish. This is the canonical record of the published
#      document, and `reference_document` on this doctype already links to it.
#      It is only populated for Update/Delete requests, where the user picks it
#      up front; a Create request publishes without ever being pointed at the
#      entry its own run created.
#
#   2. The BPMN instance's task data — `drive_file.webViewLink`, the value the
#      Drive connector returned when the file was made.
#
# So the link is resolved rather than stored: prefer the index entry, fall back
# to the run that produced it. The fallback is what makes this work for
# documents published before any of this existed.

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
		["name", "title", "status", "reference_document"],
		as_dict=True,
	)
	if not request:
		return {}

	# A completed Delete request still carries a reference_document — the user
	# picked it in order to say what to delete. Resolving it would hand back a
	# link to a file that the process has since removed from Drive.
	if request.status in NO_DOCUMENT_STATUSES:
		return {}

	# 1. The canonical index entry, when the request is pointed at one.
	if request.reference_document:
		entry = frappe.db.get_value(
			"AI Reference Index",
			request.reference_document,
			["drive_file_link", "title"],
			as_dict=True,
		)
		if entry and entry.drive_file_link:
			return {
				"url": entry.drive_file_link,
				"title": entry.title or request.title,
				"source": "reference_document",
			}

	# 2. The run that produced it. `update_field` writes status with
	#    frappe.db.set_value, so no doc hook fires at publish and nothing ever
	#    stamps the link back onto the request — the instance is the only
	#    remaining record of what was created.
	link = _link_from_process_instance(document_request)
	if link:
		return {"url": link, "title": request.title, "source": "process_instance"}

	return {}


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
