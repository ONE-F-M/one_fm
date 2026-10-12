"""Rename the PAM Licence status options: Not suspended -> Active, Detained -> Suspended.

A Select stores its label, so renaming the options on the doctype leaves every existing
licence holding a value that is no longer on the list. Frappe does not clear those - they
sit there and render as an unknown option - so the rows have to be rewritten to match.

Two tables, not one. ``PAM Licenses`` (the licence rows on PAM File) carries a Data copy of
this status fetched from the licence, and a fetch_from copy only refreshes when its parent
is next saved. Leaving it alone would show the old wording on PAM File for however long it
takes someone to re-save each file, so the denormalised copy is remapped here too.

``Inactive`` is unchanged and blank rows are left blank. The mixed-case ``Not Suspended`` is
mapped alongside the stored ``Not suspended`` - the field has been edited by hand over the
years and matching only one casing would quietly strand the other.
"""

import frappe
from frappe.query_builder import DocType

# Old label -> new label. Inactive is deliberately absent: it keeps its name.
RENAMES = (
	("Not suspended", "Active"),
	("Not Suspended", "Active"),
	("Detained", "Suspended"),
)

# The licence itself, and the fetched copy on the PAM File licence rows.
TABLES = ("PAM License Details", "PAM Licenses")


def execute():
	for doctype in TABLES:
		if not frappe.db.has_column(doctype, "status"):
			# The column arrives with the doctype sync. If it is not here yet there is
			# nothing to remap, and the next run will do it.
			continue

		table = DocType(doctype)

		for old, new in RENAMES:
			(
				frappe.qb.update(table)
				.set(table.status, new)
				.where(table.status == old)
			).run()
