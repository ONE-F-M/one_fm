# Copyright (c) 2026, ONE FM and contributors
# For license information, please see license.txt
"""WI-002594: carry an Employee master change into the sub-documents still in flight.

Civil ID, PAM file number, PAM designation and work permit salary are held on the Employee
and copied onto every Work Permit, Medical Insurance, Residency and PACI raised for them.
The copy is a `fetch_from`, which only runs when the sub-document itself is saved - so a
Civil ID issued today did not reach the four legal forms already open for that candidate,
and each of them had to be opened and re-saved by hand.

Two things this deliberately does not do.

**It does not touch a submitted document.** Those are the forms that went to the ministry;
what they say is what was submitted, and a value corrected afterwards does not change what
was filed. Only `docstatus == 0` records are updated.

**It does not save the sub-document.** `frappe.db.set_value` writes past the controller on
purpose: a Work Permit whose employee has since been marked inactive refuses to validate,
and an Employee edit must not fail because a form raised months ago can no longer be
saved. The cost is that no other hook on those documents runs, which is what is wanted -
nothing here is a state change.

The MOI address group (Governorate, Block, Street, Building) that the story also lists is
not synced: those four are not fields on Employee, on this site, on the BA site or in the
repo. They exist only on Residency, where they describe the company's registered address
rather than the employee's. Raised with the process owner rather than invented here.
"""

import frappe

from one_fm.grd.document_title import TITLE_SOURCES, document_title

# The Employee fields worth reacting to. An Employee is saved constantly, and a save that
# touched none of these cannot have changed anything a sub-document copies.
WATCHED_FIELDS = (
	"one_fm_civil_id",
	"pam_file_number",
	"one_fm_pam_designation",
	"work_permit_salary",
)

# Where each Employee field lands, per DocType. Mirrors the `fetch_from` each sub-document
# already declares - this is the same copy, made at the other end of the link. Residency's
# company_pam_file_number is the one with no fetch_from of its own; it holds the number of
# the PAM licence the employee sits under, which is what Employee.pam_file_number is.
FIELD_MAP = {
	"Work Permit": {
		"one_fm_civil_id": "civil_id",
		"pam_file_number": "pam_file_number",
		"one_fm_pam_designation": "pam_designation",
		"work_permit_salary": "work_permit_salary",
	},
	"Medical Insurance": {
		"one_fm_civil_id": "civil_id",
		"pam_file_number": "pam_file_number",
	},
	"Residency": {
		"one_fm_civil_id": "one_fm_civil_id",
		"pam_file_number": "company_pam_file_number",
		"one_fm_pam_designation": "pam_designation",
	},
	"PACI": {
		"one_fm_civil_id": "civil_id",
		"one_fm_pam_designation": "pam_designation",
	},
}

# The two whose title is derived (WI-002593). A Civil ID arriving here is exactly the
# event that should re-title them, and db_set does not run the controller that would.
TITLED_DOCTYPES = ("Work Permit", "PACI")

# A cancelled record is closed. It is docstatus 0 - the GRD workflows all give Cancelled a
# draft docstatus - so it has to be excluded by name rather than by docstatus.
CANCELLED = "Cancelled"


def sync_to_sub_documents(doc, method=None):
	"""Push the Employee's changed master fields onto the forms still in flight."""
	if doc.flags.in_insert:
		# Nothing has been raised for an employee that did not exist a moment ago.
		return

	changed = [field for field in WATCHED_FIELDS if doc.has_value_changed(field)]
	if not changed:
		return

	for doctype, field_map in FIELD_MAP.items():
		updates = {
			field_map[field]: doc.get(field) for field in changed if field in field_map
		}
		if updates:
			_apply(doctype, doc.name, updates)


def _apply(doctype, employee, updates):
	"""Write the new values onto every unsubmitted record of this type for the employee."""
	fields = ["name", *dict.fromkeys([*updates, *TITLE_SOURCES])]
	rows = frappe.get_all(
		doctype,
		filters=[
			["employee", "=", employee],
			["docstatus", "=", 0],
			["workflow_state", "!=", CANCELLED],
		],
		fields=[field for field in fields if _has_field(doctype, field)],
	)

	for row in rows:
		values = dict(updates)
		if doctype in TITLED_DOCTYPES:
			# Derived from the row as it will be, not as it was - the Civil ID that just
			# arrived is the whole reason the title changes.
			values["title"] = document_title({**row, **updates})

		# update_modified=False: the operator holding this form did not touch it, and the
		# GRD lists are sorted by modified.
		frappe.db.set_value(doctype, row["name"], values, update_modified=False)


def _has_field(doctype, fieldname):
	"""Not every sub-document carries every title source - PACI has no employee_name."""
	return fieldname == "name" or bool(frappe.get_meta(doctype).get_field(fieldname))
