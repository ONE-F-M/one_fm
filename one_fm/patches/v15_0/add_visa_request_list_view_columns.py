"""WI-002426: the Visa Request list view as the analyst configured it on the BA site.

A List View Settings row, not in_list_view flags: when such a row exists Frappe resolves
the columns from it and ignores the DocField flags entirely, so pinning the columns is the
only way to get the same list on every environment.

"status_field" is not a Visa Request field - it is the pseudo-fieldname Frappe's own list
settings use for the Status indicator column (list_settings.js::set_status_field), and it
is carried over exactly as the BA site stores it.
"""

import json

import frappe

LIST_VIEW = "Visa Request"

# Verbatim from the BA site's List View Settings row (created 2026-07-13).
BA_COLUMNS = [
	{"fieldname": "name", "label": "ID"},
	{"fieldname": "status_field", "label": "Status"},
	{"fieldname": "job_applicant", "label": "Job Applicant"},
	{"fieldname": "job_applicant_full_name", "label": "Job Applicant Full Name"},
	{"fieldname": "nationality", "label": "Nationality"},
]

# Also verbatim. Frappe stores this as the number of columns the list is allowed, which the
# BA site has one above the number of columns pinned.
TOTAL_FIELDS = "6"


def execute():
	settings = (
		frappe.get_doc("List View Settings", LIST_VIEW)
		if frappe.db.exists("List View Settings", LIST_VIEW)
		else frappe.new_doc("List View Settings")
	)
	if settings.is_new():
		settings.name = LIST_VIEW

	settings.fields = json.dumps(BA_COLUMNS)
	settings.total_fields = TOTAL_FIELDS
	settings.save(ignore_permissions=True)

	verify()


def verify():
	"""total_fields is a Select, and a value it does not offer is dropped on save."""
	saved = frappe.db.get_value("List View Settings", LIST_VIEW, ["fields", "total_fields"], as_dict=True)

	if json.loads(saved.fields) != BA_COLUMNS:
		frappe.throw(f"WI-002426: the {LIST_VIEW} list columns did not save as configured.")

	if saved.total_fields != TOTAL_FIELDS:
		frappe.throw(
			f"WI-002426: {LIST_VIEW} total_fields saved as {saved.total_fields!r}, "
			f"not {TOTAL_FIELDS!r}."
		)

	print(f"WI-002426: {LIST_VIEW} list view pinned to the BA site's columns")
