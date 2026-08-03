# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt

# One published revision of a controlled document.
#
# Every version of a document shares a single Google Drive file — the link on
# the request never changes, so bookmarks and cross-references keep working
# across revisions. The cost of that choice is that Drive only ever holds the
# *newest* text: the moment "Save Final Content to Drive" runs, the previous
# revision is gone from Drive. These records are where superseded text survives,
# which is why `content_snapshot` is written at publish and never afterwards.
#
# Rows are created by the process (the "Drive — Index Document" Script Task at
# publish) and by the backfill patch. Nothing else should write one: a version
# that no approval produced is not a version.

import frappe
from frappe.model.document import Document
from frappe.utils import cint


class AIDocumentVersion(Document):
	def before_naming(self):
		"""Guarantee the pieces the `format:` autoname interpolates.

		The name is `{document_code}-V{version}`, which is readable and citable
		("POL-0001-V2") — but only while both parts are present. A blank code
		would name every first version "-V1" and the second document to publish
		would collide on a duplicate key. Falling back to the Drive file id is
		ugly and unique, which in that order is the right trade.
		"""
		if not self.document_code:
			self.document_code = self.document or "DOC"
		if not cint(self.version):
			self.version = 1


def get_versions(document: str) -> list[dict]:
	"""Every version of a document, newest first.

	Used by the AI Reference Index form and by the tests. Kept here rather than
	inlined at each call site because "newest first" is a contract — a version
	list in creation order reads as though the oldest revision were current.
	"""
	return frappe.get_all(
		"AI Document Version",
		filters={"document": document},
		fields=[
			"name",
			"version",
			"title_at_version",
			"published_on",
			"published_by",
			"approved_by",
			"change_reason",
			"document_request",
		],
		order_by="version desc",
	)
