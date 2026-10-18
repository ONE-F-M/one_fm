import frappe

from one_fm.grd.doctype.preparation.preparation import (
	SUB_DOCUMENT_SEQUENCE,
	refresh_row_stage,
)

# The Current Stage on a Preparation row is now the first unfinished step, not the furthest
# one reached, and a cancelled document counts. Every existing row was written under the old
# rule, so each one is recomputed once here.


def execute():
	frappe.reload_doc("grd", "doctype", "preparation_record")

	pairs = set()
	for doctype in SUB_DOCUMENT_SEQUENCE:
		for document in frappe.get_all(
			doctype,
			filters={"preparation": ["is", "set"], "employee": ["is", "set"]},
			fields=["preparation", "employee"],
			distinct=True,
		):
			pairs.add((document.preparation, document.employee))

	for preparation, employee in sorted(pairs):
		refresh_row_stage(preparation, employee)
