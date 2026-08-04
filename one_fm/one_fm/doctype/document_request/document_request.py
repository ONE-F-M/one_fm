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
		self.check_required_links()
		self.check_reference_document_is_active()
		self.check_reference_document_is_controlled()
		self.check_update_source()

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
			"Document Register", self.reference_document, ["document_type", "title"], as_dict=True
		)
		if not ref:
			return
		self.document_type = ref.document_type
		if not self.title:
			self.title = ref.title

	def check_reference_document_is_active(self):
		"""Refuse to revise or withdraw a document that is already withdrawn.

		Both branches would otherwise run to completion and mean nothing: a
		second Delete re-withdraws what is already out of use, and an Update
		would quietly re-share and republish a document somebody deliberately
		took down — reactivation by side effect, bypassing the System Manager
		check that guards the real Reactivate button.
		"""
		if self.request_action == "Create" or not self.reference_document:
			return

		state = frappe.db.get_value("Document Register", self.reference_document, "lifecycle_state")
		if state != "Inactive":
			return

		frappe.throw(
			_(
				"{0} is already inactive — it has been withdrawn from use. To bring it "
				"back, use the Reactivate button on the document itself; a System Manager "
				"has to approve that. There is nothing for a {1} request to do here."
			).format(frappe.bold(self.reference_document), self.request_action)
		)

	def check_reference_document_is_controlled(self):
		"""Input material is not a controlled document, so it cannot be revised.

		Guidelines, amendment documents and the like are catalogued in the same
		register so they can be *picked as a source*. Revising one through this
		process would give it a document code and a version history, quietly
		promoting reference material into the controlled set.
		"""
		if self.request_action == "Create" or not self.reference_document:
			return

		if frappe.db.get_value("Document Register", self.reference_document, "is_input_material"):
			frappe.throw(
				_(
					"{0} is input material — reference content the process reads, not a "
					"controlled document it produced. It has no version history to add to. "
					"Pick the controlled document you want to revise, and use this one as "
					"the New Content Document instead."
				).format(frappe.bold(self.reference_document))
			)

	def check_required_links(self):
		"""Enforce the action's required links here, not just on the form.

		``mandatory_depends_on`` is evaluated **client-side only** — Frappe has no
		server-side equivalent — so it styles the field and blocks the Save button
		and nothing more. Anything that inserts a request without going through
		the form (the API, a bulk import, a test) sails past it, and the gap only
		surfaces later as a process that runs with nothing to act on.
		"""
		if self.request_action == "Create":
			return

		if not self.reference_document:
			frappe.throw(
				_("Pick the existing document this {0} request applies to.").format(self.request_action)
			)

		if self.request_action == "Update" and not self.update_source:
			frappe.throw(
				_(
					"An Update needs a New Content Document — the document holding what the "
					"revision should say. Catalogue it on Document Register first (pasting its "
					"Drive link is enough), tick Input Material, then pick it here. The wording "
					"published comes from that document, not from the AI."
				)
			)

	def check_update_source(self):
		"""The revision's content has to come from somewhere other than itself.

		On an Update the uploaded document is the authoritative content — the AI
		is only allowed to reformat it, never to invent wording. Pointing that at
		the document being revised would ask it to reformat a document into
		itself, which produces a version identical to the one before it.
		"""
		if self.request_action != "Update":
			# Only Update consumes it; a stale value on a Create/Delete would be
			# fetched by the process and silently treated as the new content.
			self.update_source = None
			return

		if self.update_source and self.update_source == self.reference_document:
			frappe.throw(
				_(
					"The New Content Document cannot be the document being revised — "
					"that would publish a new version identical to the current one. "
					"Catalogue the new content as its own entry and pick that."
				)
			)


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
#   1. Document Register.drive_file_link — written by the map's "Drive — Index
#      Document" step at publish. This is the canonical record of the published
#      document, and `reference_document` already links to it. It is only
#      populated for Update/Delete requests, where the user picks it up front;
#      a Create request publishes without ever being pointed at the entry its
#      own run created.
#
#      One link serves every revision. Because a new version overwrites the same
#      Drive file rather than making a new one, this URL never goes stale — it
#      opens whatever the current version is.
#
#   2. The BPMN instance's task data — `drive_file.webViewLink`, the value the
#      Drive connector returned when the file was made.
#
# Resolution is therefore a repair path, not the read path. It fills the field
# the first time anyone looks, so each request pays it once rather than on
# every view.

# Statuses where there is no document to open, even though the request may
# still name one.
#
# "Deleted" used to be listed here, back when the Delete branch trashed the
# Drive file: resolving a link then handed back a URL to a file that no longer
# existed. Delete now withdraws the document instead — the file, its content and
# every version are kept, and only the sharing is revoked — so the link resolves
# and hiding it would be wrong. The form says the document is inactive rather
# than pretending it is gone, because a request that says "withdrawn" while
# offering no way to see *what* was withdrawn is useless to an auditor.
NO_DOCUMENT_STATUSES = ("Request Rejected",)


@frappe.whitelist()
def get_published_document_link(document_request: str) -> dict:
	"""Return the Google Docs link for a published Document Request.

	Returns ``{"url": ..., "title": ..., "source": ..., "lifecycle": ...,
	"version": ...}``, or ``{}`` when no link can be found — an unpublished
	request, or a published one whose run predates the Drive integration.
	``source`` says which of the two routes answered, so a support question can
	be diagnosed from the response alone. ``lifecycle`` lets the form warn that a
	document has been withdrawn instead of silently offering a link to something
	nobody should be following.
	"""
	if not frappe.has_permission("Document Request", "read", doc=document_request):
		frappe.throw(_("Not permitted to read this Document Request."), frappe.PermissionError)

	request = frappe.db.get_value(
		"Document Request",
		document_request,
		["name", "title", "status", "reference_document", "document_link", "document_version"],
		as_dict=True,
	)
	if not request:
		return {}

	if request.status in NO_DOCUMENT_STATUSES:
		return {}

	lifecycle = _lifecycle_of(request.reference_document)

	# The stored field is the answer whenever it is set — no lookups at all.
	if request.document_link:
		return {
			"url": request.document_link,
			"title": request.title,
			"source": "document_link",
			"lifecycle": lifecycle,
			"version": request.document_version,
		}

	# 1. The canonical index entry, when the request is pointed at one.
	source = url = None
	title = request.title
	if request.reference_document:
		entry = frappe.db.get_value(
			"Document Register",
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
	return {
		"url": url,
		"title": title,
		"source": source,
		"lifecycle": lifecycle,
		"version": request.document_version,
	}


def _lifecycle_of(reference_document: str | None) -> str | None:
	"""Whether the document this request points at is still in use.

	``None`` when the request names no document, or names one that is no longer
	in the register — neither is an error, and neither justifies claiming the
	document is active.
	"""
	if not reference_document:
		return None
	return frappe.db.get_value("Document Register", reference_document, "lifecycle_state")


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
