"""Turn on Actions > Edit for the Medical Appointment list view.

Medical Appointment has an active workflow, and Frappe hides bulk edit on a workflow
DocType unless its List View Settings record has `allow_edit` = 1 (`is_bulk_edit_allowed`
in list_view.js). DocType has no `allow_edit` property, so medical_appointment.json is not
the place for it.

Not shipped as a fixture: List View Settings also holds per-site column and sidebar
choices, which a fixture would overwrite on every migrate. Only the flag is touched.
"""

import frappe

DOCTYPE = "List View Settings"
LIST_VIEW = "Medical Appointment"


def execute():
	if frappe.db.exists(DOCTYPE, LIST_VIEW):
		frappe.db.set_value(DOCTYPE, LIST_VIEW, "allow_edit", 1)
	else:
		frappe.get_doc({"doctype": DOCTYPE, "name": LIST_VIEW, "allow_edit": 1}).insert(
			ignore_permissions=True
		)

	verify()


def verify():
	if not frappe.db.get_value(DOCTYPE, LIST_VIEW, "allow_edit"):
		raise frappe.ValidationError("List View Settings allow_edit is still off for Medical Appointment")
