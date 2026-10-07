"""WI-002593: give every existing Work Permit and PACI the title it should have had.

The title is derived on save, and these documents are not going to be saved again - most
of them are submitted. Without a backfill the change would only reach records touched from
today, and every historical row would keep showing a blank title in the list, in Link
fields and on dashboard badges.
"""

import frappe

from one_fm.grd.document_title import TITLE_SOURCES, document_title

DOCTYPES = ("Work Permit", "PACI")

# Big enough that the whole table is a handful of round trips, small enough that no single
# transaction holds thousands of rows open.
BATCH_SIZE = 500


def execute():
	for doctype in DOCTYPES:
		backfill(doctype)


def backfill(doctype):
	rows = frappe.get_all(
		doctype,
		filters=[["title", "in", [None, ""]]],
		fields=["name", *TITLE_SOURCES],
	)

	written = 0
	for index, row in enumerate(rows, start=1):
		title = document_title(row)
		if not title:
			# A record naming no employee at all. There is nothing to call it, and an
			# invented title would be worse than an empty one.
			continue

		# update_modified=False: the backfill is this patch's doing, and the GRD lists
		# sort by modified.
		frappe.db.set_value(doctype, row.name, "title", title, update_modified=False)
		written += 1

		if index % BATCH_SIZE == 0:
			frappe.db.commit()

	frappe.db.commit()
	print(f"WI-002593: titled {written} of {len(rows)} {doctype} records")
