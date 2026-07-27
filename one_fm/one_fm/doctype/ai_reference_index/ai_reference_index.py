# Copyright (c) 2026, one-fm and contributors
# For license information, please see license.txt

import re

import frappe
from frappe import _
from frappe.model.document import Document

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


class AIReferenceIndex(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		content: DF.LongText | None
		document_type: DF.Data | None
		drive_file_id: DF.Data | None
		drive_file_link: DF.Data | None
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
		except Exception:
			if not self.title:
				self.title = self.drive_file_id
			return

		try:
			if not self.title or not self.drive_file_link:
				meta = (
					gd._get_service()
					.files()
					.get(fileId=self.drive_file_id, fields="name,webViewLink", supportsAllDrives=True)
					.execute()
				)
				if not self.title:
					self.title = meta.get("name") or self.drive_file_id
				if not self.drive_file_link:
					self.drive_file_link = meta.get("webViewLink")
			if not self.content:
				self.content = gd.download_file_text(self.drive_file_id)
		except Exception:
			frappe.log_error(
				title="AI Reference Index: Drive auto-fill failed",
				message=frappe.get_traceback(),
			)
			if not self.title:
				self.title = self.drive_file_id
