# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""
Rename AI Reference Index → Document Register, AI Document Version → Document Revision.

Neither name described what the doctype had become. The ``AI`` prefix was
vestigial — nothing about either is AI-specific — and ``Index`` implied a search
index, which the register is not: it is the list of documents the organisation
controls, plus the reference material those documents are built from. ``Register``
is the term the standards use for exactly that. ``Revision`` is likewise the term
of art for an issued version of a controlled document, and it avoids being read as
Frappe's own ``Version`` doctype, which tracks field-level edits and means
something entirely different.

**This must run pre-model-sync.** If the doctype sync ran first it would create
empty ``Document Register`` and ``Document Revision`` tables from the JSON while
the populated ``AI *`` tables sat beside them, and the rename would then fail on
a name that already exists.

Renaming a DocType renames its table and repoints every Link field at it, so
``Document Request.reference_document`` and ``Document Revision.document`` follow
automatically. No-ops on a site that never had the old names — a fresh install
creates them from the JSON already renamed.
"""

import frappe

RENAMES = (
	("AI Reference Index", "Document Register"),
	("AI Document Version", "Document Revision"),
)


def execute():
	for old, new in RENAMES:
		if not frappe.db.exists("DocType", old):
			continue

		if frappe.db.exists("DocType", new):
			# Both present means a sync already created the new one empty. Merging
			# is not something to guess at — the rows, the naming series and the
			# Link targets all have to be reconciled by hand.
			frappe.log_error(
				title=f"rename_document_register_and_revision: {old} and {new} both exist",
				message=(
					f"Cannot rename {old!r} to {new!r} because {new!r} already exists. "
					"This happens when the doctype sync ran before this patch. Reconcile "
					"the two by hand: move any rows out of the empty one, delete it, then "
					"re-run this patch."
				),
			)
			continue

		frappe.rename_doc("DocType", old, new, force=True)
		print(f"Renamed DocType {old!r} -> {new!r}")

	frappe.db.commit()
