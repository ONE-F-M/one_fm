"""WI-002887: turn on Actions > Edit for the four GRD list views.

Frappe hides bulk edit on any DocType that has a workflow unless it is switched on
explicitly. From `list_view.js`:

    const is_bulk_edit_allowed = (doctype) => {
        // Check settings if there is a workflow defined, otherwise directly allow
        if (frappe.model.has_workflow(doctype)) {
            return !!this.list_view_settings?.allow_edit;
        }
        return true;
    };

All four of these carry an active workflow, so Actions > Edit is absent on all four today
and no DocType property brings it back - the switch is `allow_edit` on **List View
Settings**, a record named after the DocType. (DocType itself has no `allow_edit`; the
three DocTypes that do are List View Settings, Web Form and Workflow Document State.)

The record is created here rather than shipped as a fixture because List View Settings is
a per-site preference: it also carries the operator's own column choices and sidebar
options, and a fixture would overwrite those on every migrate. Only the one flag is
touched, and an existing record keeps everything else it holds.
"""

import frappe

DOCTYPE = "List View Settings"

# Named as the story names them. List View Settings is autonamed by prompt, and the name
# IS the DocType whose list it configures.
LIST_VIEWS = ("Work Permit", "Medical Insurance", "Residency", "PACI")


def execute():
	for doctype in LIST_VIEWS:
		if frappe.db.exists(DOCTYPE, doctype):
			# Only the flag. The rest of the record is whoever configured the list's.
			frappe.db.set_value(DOCTYPE, doctype, "allow_edit", 1)
			continue

		frappe.get_doc({"doctype": DOCTYPE, "name": doctype, "allow_edit": 1}).insert(
			ignore_permissions=True
		)

	verify()


def verify():
	missing = [
		doctype
		for doctype in LIST_VIEWS
		if not frappe.db.get_value(DOCTYPE, doctype, "allow_edit")
	]
	if missing:
		frappe.throw(
			f"WI-002887: bulk edit is still off for {missing}. Those list views carry a "
			"workflow, so Actions > Edit stays hidden without it."
		)
