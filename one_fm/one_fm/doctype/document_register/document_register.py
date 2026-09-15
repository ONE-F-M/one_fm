# Copyright (c) 2026, one-fm and contributors
# For license information, please see license.txt

# The register of controlled documents — one row per document, keyed on the
# Google Drive file id.
#
# One row per *document*, not per version. Every revision of a document shares a
# single Drive file, so the file id stays the stable identity for the document's
# whole life and the link handed to staff never breaks. `content` and
# `current_version` describe the revision Drive currently holds; superseded
# revisions live on Document Revision.
#
# Withdrawal is reversible by construction. Nothing here deletes: an `Inactive`
# document keeps its file, its content and every version snapshot, and only
# loses its Drive sharing — which is the part staff actually experience as
# "it's gone".
#
# Drive access here authenticates as ONE FM's own service account (ONEFM General
# Setting > Google > Service Account JSON), not as a BPMN connector — see
# `_drive_service`. The register is ONE FM's catalogue; the connectors are how
# processes create the files it catalogues. Both accounts therefore need to be
# members of the same Shared Drive.

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, now_datetime

# Prefix per document type for the readable code (POL-0001, SOP-0004).
#
# A naming convention rather than a configuration: changing a prefix after
# documents are issued renames nothing already allocated and would leave one
# type with two prefixes. A type absent from this map falls back to its own
# first three letters, so a new document type indexes correctly before anyone
# remembers to add it here.
CODE_PREFIXES = {
	"Policy": "POL",
	"SOP": "SOP",
	"Manual": "MAN",
	"Guideline": "GDL",
}

# The starter grant the process applies at publish (the map's "Set Drive Sharing
# Permissions" task). Reactivation has to restore *something*, and this is the
# only sharing the system ever grants of its own accord.
DEFAULT_GRANTS = [{"type": "domain", "domain": "one-fm.com", "role": "reader"}]

# A Google Drive/Docs/Slides id is the token after /d/ (files) or /folders/
# in a share link, the value of an ?id= query param, or an already-bare id.
_ID_IN_PATH = re.compile(r"/(?:d|folders)/([A-Za-z0-9_-]{10,})")
_ID_IN_QUERY = re.compile(r"[?&]id=([A-Za-z0-9_-]{10,})")


def _drive_id(value):
	"""Accept a Drive link OR a bare id and return the id (best-effort)."""
	if not value:
		return ""
	s = str(value).strip()
	m = _ID_IN_PATH.search(s) or _ID_IN_QUERY.search(s)
	return m.group(1) if m else s


class DocumentRegister(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		content: DF.LongText | None
		current_version: DF.Int
		deactivated_by: DF.Link | None
		deactivated_on: DF.Datetime | None
		deactivated_via_request: DF.Link | None
		deactivation_reason: DF.SmallText | None
		document_code: DF.Data | None
		document_type: DF.Data | None
		drive_file_id: DF.Data | None
		drive_file_link: DF.Data | None
		lifecycle_state: DF.Literal["Active", "Inactive"]
		source_process: DF.Link | None
		title: DF.Data | None
	# end: auto-generated types

	def before_insert(self):
		# Resolve the id before autonaming (autoname = field:drive_file_id).
		self._resolve_drive_file_id()

	def validate(self):
		self._resolve_drive_file_id()
		self._autofill_from_drive()

	def _resolve_drive_file_id(self):
		"""Require one of Drive File ID / Drive File Link; normalize either into
		drive_file_id (users may paste a link into either field)."""
		fid = _drive_id(self.drive_file_id) or _drive_id(self.drive_file_link)
		if not fid:
			frappe.throw(_("Provide a Google Drive file id or link."))
		self.drive_file_id = fid

	def _autofill_from_drive(self):
		"""Fill title / drive_file_link / content from Drive when blank, so a user
		only needs to supply the id or link. Best-effort and non-fatal: if the
		Drive integration is unavailable or the file can't be read, the record
		still saves (content can be refreshed later)."""
		if self.title and self.drive_file_link and self.content:
			return  # nothing to fill

		try:
			from one_bpmn.one_bpmn.integrations import google_drive as gd

			service = _drive_service()
		except Exception:
			if not self.title:
				self.title = self.drive_file_id
			return

		try:
			if not self.title or not self.drive_file_link:
				meta = (
					service.files()
					.get(fileId=self.drive_file_id, fields="name,webViewLink", supportsAllDrives=True)
					.execute()
				)
				if not self.title:
					self.title = meta.get("name") or self.drive_file_id
				if not self.drive_file_link:
					self.drive_file_link = meta.get("webViewLink")
			if not self.content:
				self.content = gd.download_file_text(self.drive_file_id, service=service)
		except Exception as e:
			frappe.log_error(
				title="Document Register: Drive auto-fill failed",
				message=frappe.get_traceback(),
			)
			self._warn_autofill_failed(e)
			if not self.title:
				self.title = self.drive_file_id

	def _warn_autofill_failed(self, error):
		"""Say so on screen. Failing quietly is what makes this expensive.

		The record still saves — a catalogue entry blocked by a transient API
		problem is worse than one with a placeholder title. But until now the
		only trace was an Error Log entry, so pasting a link the service account
		cannot read looked exactly like pasting one it can: the fields simply
		stayed empty and nothing said why.

		Google answers 404, not 403, for a file you have no permission on, so
		"File not found" almost always means "not shared with us" rather than
		"does not exist" — and guessing wrong sends people looking for a
		deleted file that is sitting right there in their Drive.
		"""
		text = str(error)
		if "File not found" in text or "404" in text or "notFound" in text:
			account = _service_account_email() or "ONE FM's Google service account"
			frappe.msgprint(
				_(
					"Could not read {0} from Google Drive, so the title and content were "
					"not filled in.<br><br>Drive reports this the same way whether a file "
					"is missing or simply not shared, and it is almost always the latter. "
					"Share the file with <b>{1}</b> (Viewer is enough) and save again."
				).format(frappe.bold(self.drive_file_id), account),
				title=_("Drive file not accessible"),
				indicator="orange",
			)
			return

		frappe.msgprint(
			_(
				"Could not read this file from Google Drive, so the title and content "
				"were not filled in. The record has been saved — see the Error Log for "
				"the reason, then save again to retry."
			),
			title=_("Drive auto-fill failed"),
			indicator="orange",
		)


def _drive_service():
	"""Drive client for the register, as ONE FM's own service account.

	The register is ONE FM's catalogue, so it authenticates as ONE FM rather than
	borrowing a BPMN connector's key — the connectors create these files, this
	account reads and shares them, and each can now be rotated alone.

	The consequence to know about: both accounts must be members of the same
	Shared Drive. Drive answers 404 for a file an account cannot see, so a
	missing membership looks exactly like a deleted document (which is what
	``_warn_autofill_failed`` exists to explain).

	one_bpmn's Drive helpers are still reused — they take an optional
	``service``, so only the identity differs, not the .docx/.pptx handling.
	"""
	from one_fm.one_fm.google_credentials import get_drive_service

	return get_drive_service()


def _service_account_email():
	"""Which Google identity ONE FM uses, for an actionable error message."""
	from one_fm.one_fm.google_credentials import service_account_email

	return service_account_email()


def code_prefix(document_type: str) -> str:
	"""The code prefix for a document type — mapped, else its first 3 letters."""
	document_type = (document_type or "").strip()
	if document_type in CODE_PREFIXES:
		return CODE_PREFIXES[document_type]
	return (document_type[:3] or "DOC").upper()


def allocate_document_code(document_type: str) -> str:
	"""Next free code for a document type, e.g. ``POL-0003``.

	A code is never reused. A reissued POL-0002 pointing at different content is
	exactly the confusion a controlled-document register exists to prevent, so
	the number comes from the framework's own ``tabSeries`` counter — which is
	row-locked and, crucially, does not go backwards when a document is deleted
	from the register. Deriving it from the surviving rows instead would hand out
	POL-0001 again the moment the only Policy was removed.

	Gaps are therefore possible and are not a problem; collisions would be.
	"""
	from frappe.model.naming import getseries

	prefix = code_prefix(document_type)
	key = prefix + "-"
	_raise_series_floor(key, _highest_issued(prefix))
	return key + getseries(key, 4)


def _highest_issued(prefix: str) -> int:
	"""The largest number already present in a code for this prefix.

	Needed as a floor because codes issued before the counter existed — by the
	migration that seeded the register, or by hand — are invisible to
	``tabSeries``, and ``document_code`` is unique: handing out a number that is
	already on a row does not produce a duplicate code, it produces a failed
	publish.
	"""
	issued = frappe.db.sql(
		"""
		select `document_code` from `tabDocument Register`
		where `document_code` like %s
		""",
		(prefix + "-%",),
	)

	highest = 0
	for (code,) in issued:
		try:
			highest = max(highest, int(str(code).rsplit("-", 1)[1]))
		except (IndexError, ValueError):
			# A hand-edited code that will not parse must not stop a publish.
			continue
	return highest


def _raise_series_floor(key: str, floor: int) -> None:
	"""Make sure the series is at least ``floor``, never lowering it."""
	if not floor:
		return
	frappe.db.sql(
		"""
		insert into `tabSeries` (`name`, `current`) values (%s, %s)
		on duplicate key update `current` = greatest(`current`, %s)
		""",
		(key, cint(floor), cint(floor)),
	)


@frappe.whitelist()
def deactivate(document: str, reason: str = None, via_request: str = None, revoke: bool = True) -> dict:
	"""Withdraw a document from use without destroying anything.

	Shared by the process (the map's "Deactivate Document" Script Task) and by
	the Deactivate button, so the two cannot drift into meaning different things.

	Revoking the Drive sharing is the half users notice — a document flagged
	Inactive while still shared domain-wide is still open to everyone holding
	the link. ``revoke=False`` exists for the process, where the very next step
	is a "Revoke Sharing" connector task: the Drive call belongs on the diagram
	where a reader can see it happen, not hidden inside a script. A failure to
	revoke is reported back rather than swallowed, but it does not block the
	flag — leaving the register saying "Active" because Drive was unreachable is
	worse than a flag that is ahead of the sharing.
	"""
	if not frappe.has_permission("Document Register", "write", doc=document):
		frappe.throw(_("Not permitted to withdraw this document."), frappe.PermissionError)

	doc = frappe.get_doc("Document Register", document)

	revoked = 0
	skipped = []
	revoke_error = None
	if revoke:
		try:
			from one_bpmn.one_bpmn.integrations.google_drive import revoke_permissions

			outcome = revoke_permissions(doc.drive_file_id, scope="all", service=_drive_service())
			revoked = len(outcome["removed"])
			skipped = outcome["skipped"]
		except Exception as e:
			revoke_error = str(e)
			frappe.log_error(
				title="Document Register: deactivate could not revoke Drive sharing",
				message=frappe.get_traceback(),
			)

	doc.lifecycle_state = "Inactive"
	doc.deactivated_on = now_datetime()
	doc.deactivated_by = frappe.session.user
	doc.deactivation_reason = reason
	doc.deactivated_via_request = via_request
	doc.save()

	return {"ok": True, "revoked": revoked, "skipped": skipped, "revoke_error": revoke_error}


@frappe.whitelist()
def reactivate(document: str, reason: str = None) -> dict:
	"""Return a withdrawn document to active use — the reverse of ``deactivate``.

	Deliberately *not* a Document Request: re-issuing a document that was
	withdrawn in error is a correction to the register, and routing it through
	drafting and two approvals would mint a new version of text that never
	changed.

	Restores the domain grant as well as the flag, because a document that is
	Active in Frappe but unshared in Drive looks available and isn't — the worst
	of the three possible states.
	"""
	if "System Manager" not in frappe.get_roles():
		frappe.throw(
			_("Only a System Manager can reactivate a controlled document."), frappe.PermissionError
		)

	doc = frappe.get_doc("Document Register", document)
	if doc.lifecycle_state == "Active":
		return {"ok": True, "already_active": True, "shared": 0}

	granted = 0
	share_error = None
	try:
		from one_bpmn.one_bpmn.integrations.google_drive import set_permissions

		granted = len(
			set_permissions(doc.drive_file_id, DEFAULT_GRANTS, service=_drive_service())
		)
	except Exception as e:
		share_error = str(e)
		frappe.log_error(
			title="Document Register: reactivate could not restore Drive sharing",
			message=frappe.get_traceback(),
		)

	doc.lifecycle_state = "Active"
	doc.deactivated_on = None
	doc.deactivated_by = None
	doc.deactivated_via_request = None
	doc.deactivation_reason = None
	doc.save()

	doc.add_comment(
		"Info",
		_("Reactivated by {0}.").format(frappe.session.user)
		+ (_(" Reason: {0}").format(reason) if reason else "")
		+ (
			_(" Drive sharing could not be restored: {0}").format(share_error)
			if share_error
			else ""
		),
	)

	return {"ok": True, "shared": granted, "share_error": share_error}


@frappe.whitelist()
def get_version_history(document: str) -> list:
	"""Every published revision of a document, newest first."""
	if not frappe.has_permission("Document Register", "read", doc=document):
		frappe.throw(_("Not permitted to read this document."), frappe.PermissionError)

	from one_fm.one_fm.doctype.document_revision.document_revision import get_versions

	return get_versions(document)
