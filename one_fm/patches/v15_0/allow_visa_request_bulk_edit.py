"""WI-002446 AC 1: let a Recruiter set the GRD Operator on several requests at once.

Frappe offers the list view's Edit action only when `is_bulk_edit_allowed()` says so
(list_view.js), and for a doctype carrying a workflow that answer comes from one place:
the `allow_edit` flag on its List View Settings row. Visa Request has an active workflow,
and the row WI-002426 brought over from the BA site has the flag off - which is how their
site has it, because bulk editing is the thing this story adds.

Without this the Actions menu simply has no Edit entry, whatever the fields themselves
allow, and the criterion cannot be met at all.
"""

import frappe

LIST_VIEW = "Visa Request"


def execute():
	settings = (
		frappe.get_doc("List View Settings", LIST_VIEW)
		if frappe.db.exists("List View Settings", LIST_VIEW)
		else frappe.new_doc("List View Settings")
	)
	if settings.is_new():
		# add_visa_request_list_view_columns runs before this and creates the row, so this
		# is only reached where that has not run yet - the columns it pins are its own
		# business and are left to it.
		settings.name = LIST_VIEW

	settings.allow_edit = 1
	settings.save(ignore_permissions=True)

	if not frappe.db.get_value("List View Settings", LIST_VIEW, "allow_edit"):
		frappe.throw(f"WI-002446: bulk edit is still switched off for {LIST_VIEW}.")

	print(f"WI-002446: {LIST_VIEW} list view allows bulk edit")
