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
		self.check_source_guideline_is_a_guideline()
		self.check_source_documents_are_active()

	def set_requester_defaults(self):
		"""Capture the requester from whoever is filing the request.

		The field is read-only on the form, so this is the only thing that fills
		it: a request is always filed by the person signed in, and typing it was
		how one person's request ended up under someone else's name. An existing
		value is left alone so a request created by an integration or a migration
		keeps the requester it was given.

		Because nobody can type it, an unresolvable requester has to be said out
		loud rather than left blank for the mandatory check to reject with
		"Requester is required" — which would be true and useless.
		"""
		if self.requester:
			return

		employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
		if employee:
			self.requester = employee
			self.fill_requester_chain()
			return

		if self.is_new():
			frappe.throw(
				_(
					"There is no Employee record linked to {0}, so this request cannot record "
					"who is asking for the document. Ask HR to set the User ID on that "
					"employee record, then try again."
				).format(frappe.bold(frappe.session.user)),
				title=_("No Employee Record"),
			)

	def fill_requester_chain(self):
		"""Resolve requester → approver → approver_user here, not via fetch_from.

		``approver`` is declared ``fetch_from: requester.reports_to`` and
		``approver_user`` hangs off *that*. Frappe resolves fetch_from BEFORE
		validate, so a requester captured during validate arrives too late: the
		chain stays empty and the request is refused for having no approver — on a
		requester whose line manager is set. Worse than the refusal, an approver
		that resolved late would leave ``approver_user`` blank, and that is the
		field the map assigns both approval tasks to.

		Only fills blanks, so a value supplied deliberately is never overwritten.
		"""
		if not self.requester:
			return

		chain = _requester_chain(self.requester)
		if not chain:
			return

		if not self.requester_user:
			self.requester_user = chain.get("requester_user")
		if not self.approver:
			self.approver = chain.get("approver")
		# Not chain["approver_user"]: an approver supplied deliberately is not
		# necessarily the requester's line manager, and their user must follow the
		# approver actually on the request.
		if self.approver and not self.approver_user:
			self.approver_user = frappe.db.get_value("Employee", self.approver, "user_id")

	def check_approver_resolved(self):
		if self.requester and not self.approver:
			frappe.throw(
				_(
					"Could not resolve an approver for {0} — their Employee record has no "
					"'Reports To' (line manager) set. Set it on the Employee record first."
				).format(self.requester)
			)

	def apply_reference_document_defaults(self):
		"""Fill the blanks from the reference, but REFUSE a type mismatch.

		This used to overwrite ``document_type`` from the register entry
		outright. That hid a real mistake instead of reporting it: a requester
		who chose SOP and then picked a Policy document was silently switched to
		Policy — a different template, a different code series, and a request
		that no longer said what they asked for. The two have to agree, and the
		person is the one who should decide which of the two was wrong.

		An empty type is still filled in, because there is nothing to disagree
		with — that is a default, not a correction.
		"""
		if self.request_action == "Create" or not self.reference_document:
			return
		ref = frappe.db.get_value(
			"Document Register", self.reference_document, ["document_type", "title"], as_dict=True
		)
		if not ref:
			return

		if not self.document_type:
			self.document_type = ref.document_type
		elif ref.document_type and self.document_type != ref.document_type:
			frappe.throw(
				_(
					"Document Type does not match the document you picked. This request says "
					"{0}, but {1} is a {2} in the Document Register. A revision keeps the "
					"document's own type — change the Document Type to {2}, or pick a {0} "
					"document instead."
				).format(
					frappe.bold(self.document_type),
					frappe.bold(self.reference_document),
					frappe.bold(ref.document_type),
				),
				title=_("Document Type Mismatch"),
			)

		if not self.title:
			self.title = ref.title

	def check_source_guideline_is_a_guideline(self):
		"""The guideline a Create is written from has to actually be a guideline.

		``source_guideline`` says *how* to write the document — structure, tone,
		the section rules. Point it at a Policy or an SOP and the drafting task is
		handed a finished document as its instructions, which is how a request for
		one subject comes back written about another. The picker filters to
		Guideline; this is the half that also holds for the API and for imports.
		"""
		if self.request_action != "Create" or not self.source_guideline:
			return

		kind = frappe.db.get_value("Document Register", self.source_guideline, "document_type")
		if kind and kind != "Guideline":
			frappe.throw(
				_(
					"Source Guideline must be a Guideline. {0} is a {1} — a finished "
					"document, not instructions for writing one. Pick the guideline that "
					"describes how a {2} should be written."
				).format(frappe.bold(self.source_guideline), frappe.bold(kind), self.document_type or _("document")),
				title=_("Not a Guideline"),
			)

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

	def check_source_documents_are_active(self):
		"""A withdrawn document is not usable as SOURCE material either.

		``check_reference_document_is_active`` already refuses to revise or
		withdraw an inactive document. The two fields that point the other way —
		the guideline a Create is generated from, and the New Content Document an
		Update takes its wording from — had no such check, so a withdrawn document
		could still be read and its content published into a live one. Withdrawing
		is how this system says "stop using this"; quietly using it as the source
		of a new document is the same mistake with an extra step.

		The pickers filter these fields to Active as well, but that is Frappe's
		``link_filters``, which runs in the browser. It shapes the dropdown and
		nothing else — the API, an import and a test all sail past it, which is
		exactly the gap ``check_required_links`` was written for.
		"""
		fields = (("source_guideline", "Create", _("Source Guideline")),)
		for fieldname, action, label in fields:
			name = self.get(fieldname)
			if not name or self.request_action != action:
				continue
			if frappe.db.get_value("Document Register", name, "lifecycle_state") != "Inactive":
				continue
			frappe.throw(
				_(
					"{0} is inactive — it has been withdrawn from use, so it cannot be the "
					"{1}. Publishing its content into a live document would put withdrawn "
					"material back into circulation. Pick an active document, or reactivate "
					"that one first."
				).format(frappe.bold(name), label)
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

		if self.request_action == "Update" and not (self.requirement_text or "").strip():
			# An Update used to require a New Content Document holding the finished
			# wording. It now works the way a Create does: Requirement says what to
			# change and the existing document supplies everything it does not
			# mention. That makes Requirement the one thing an Update cannot do
			# without — an Update with nothing to change would republish the
			# document unaltered as a new version.
			frappe.throw(
				_(
					"Say what the revision should change, in Requirement. The existing "
					"document supplies everything you do not mention, so describe only the "
					"change — an Update with no requirement would publish a new version "
					"identical to the current one."
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
NO_DOCUMENT_STATES = ("Request Rejected",)


def _requester_chain(employee: str) -> dict:
	"""The employee's own user, their line manager, and that manager's user.

	Shared by validate and by the form so both answer "who is asking and who
	approves" the same way. Two implementations of that drift, and a form that
	shows one approver while the save records another is worse than a form that
	shows nothing.
	"""
	row = frappe.db.get_value("Employee", employee, ["user_id", "reports_to"], as_dict=True)
	if not row:
		return {}

	approver = row.get("reports_to")
	return {
		"requester_user": row.get("user_id"),
		"approver": approver,
		"approver_user": (
			frappe.db.get_value("Employee", approver, "user_id") if approver else None
		),
	}


@frappe.whitelist()
def get_requester_defaults() -> dict:
	"""Who the signed-in user is, for a request that has not been saved yet.

	The requester is captured in validate, which is the right place to *enforce*
	it and far too late to *show* it: the field is read-only, so a new request
	opens with the requester and the whole approval chain empty, and Frappe hides
	empty read-only fields — the column is simply absent. The requester cannot
	tell whether the system knows who they are, or who will be asked to approve
	what they are about to write.

	Uses the same lookup validate uses, so the form cannot show one requester and
	save another. Returns {} when the user has no Employee record: the form says
	so at open time instead of letting a filled-in request fail on save.
	"""
	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	if not employee:
		return {}

	return {"requester": employee, **_requester_chain(employee)}


def _requester_chain(employee: str) -> dict:
	"""The employee's own user, their line manager, and that manager's user.

	Shared by validate and by the form so both answer "who is asking and who
	approves" the same way. Two implementations of that drift, and a form that
	shows one approver while the save records another is worse than a form that
	shows nothing.
	"""
	row = frappe.db.get_value("Employee", employee, ["user_id", "reports_to"], as_dict=True)
	if not row:
		return {}

	approver = row.get("reports_to")
	return {
		"requester_user": row.get("user_id"),
		"approver": approver,
		"approver_user": (
			frappe.db.get_value("Employee", approver, "user_id") if approver else None
		),
	}


@frappe.whitelist()
def get_requester_defaults() -> dict:
	"""Who the signed-in user is, for a request that has not been saved yet.

	The requester is captured in validate, which is the right place to *enforce*
	it and far too late to *show* it: the field is read-only, so a new request
	opens with the requester and the whole approval chain empty, and Frappe hides
	empty read-only fields — the column is simply absent. The requester cannot
	tell whether the system knows who they are, or who will be asked to approve
	what they are about to write.

	Uses the same lookup validate uses, so the form cannot show one requester and
	save another. Returns {} when the user has no Employee record: the form says
	so at open time instead of letting a filled-in request fail on save.
	"""
	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	if not employee:
		return {}

	return {"requester": employee, **_requester_chain(employee)}


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
		["name", "title", "workflow_state", "reference_document", "document_link", "document_version"],
		as_dict=True,
	)
	if not request:
		return {}

	if request.workflow_state in NO_DOCUMENT_STATES:
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

	# 2. The run that produced it. The map applies the state with
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
