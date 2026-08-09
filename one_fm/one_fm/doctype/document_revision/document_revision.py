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
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint


class DocumentRevision(Document):
	def validate(self):
		self.refuse_empty_snapshot()

	def refuse_empty_snapshot(self):
		"""A revision with no content is not a revision.

		This is the last line of defence on the publish path, and it earns its
		place: a drafting step that timed out wrote nothing to
		``document_markdown``, the process carried on regardless, and a Policy
		was published, indexed and issued a code and a version — with an empty
		Drive file and an empty snapshot behind it. Nobody was told.

		Refusing here stops the record that makes it *official*. Whatever failed
		upstream, an issued revision that preserves nothing is worse than no
		revision at all: the register would assert that this text was approved,
		and the text is not there to read.
		"""
		# .strip() alone is not enough. A Drive text export always begins with a
		# BOM, and U+FEFF is a *format* character, not whitespace — so an empty
		# document exports as "\ufeff" and sails straight through a truthiness
		# or .strip() check. Zero-width space gets the same treatment.
		if (self.content_snapshot or "").strip("\ufeff\u200b \t\r\n"):
			return

		frappe.throw(
			_(
				"Refusing to record version {0} of {1} with no content. The snapshot is "
				"the only surviving copy of a revision — Drive keeps just the newest "
				"text — so an empty one would leave the register asserting an approval "
				"for a document nobody can read. Check whether the drafting step "
				"failed before republishing."
			).format(self.version, self.document_code or self.document),
			title=_("Empty revision"),
		)

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

	Used by the Document Register form and by the tests. Kept here rather than
	inlined at each call site because "newest first" is a contract — a version
	list in creation order reads as though the oldest revision were current.
	"""
	return frappe.get_all(
		"Document Revision",
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
