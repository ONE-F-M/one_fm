"""WI-003499: turn on Actions > Edit for the Medical Appointment list view.

Medical Appointment has an active workflow, and Frappe hides bulk edit on a workflow
DocType unless its List View Settings record has `allow_edit` = 1 (`is_bulk_edit_allowed`
in list_view.js). No such record exists for Medical Appointment, so Actions > Edit is
missing today. DocType has no `allow_edit` property, so medical_appointment.json is not
the place for it.

The record is created here rather than shipped as a fixture because List View Settings
is a per-site preference (column and sidebar choices); a fixture would overwrite those on
every migrate. Only the one flag is touched, and an existing record keeps everything else.

Not added to LIST_VIEWS in allow_bulk_edit_on_grd_list_views: that patch has already run,
so a new name there would never execute.
"""

import frappe

DOCTYPE = "List View Settings"
LIST_VIEW = "Medical Appointment"


def execute():
	if frappe.db.exists(DOCTYPE, LIST_VIEW):
		# Only the flag. The rest of the record is whoever configured the list's.
		frappe.db.set_value(DOCTYPE, LIST_VIEW, "allow_edit", 1)
	else:
		frappe.get_doc({"doctype": DOCTYPE, "name": LIST_VIEW, "allow_edit": 1}).insert(
			ignore_permissions=True
		)

	verify()


def verify():
	if not frappe.db.get_value(DOCTYPE, LIST_VIEW, "allow_edit"):
		frappe.throw(
			f"WI-003499: bulk edit is still off for {LIST_VIEW}. The list view carries a "
			"workflow, so Actions > Edit stays hidden without it."
		)
