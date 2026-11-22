"""Turn on Actions > Edit for the Candidate Country Process and Arrival and Deployment lists.

Frappe hides bulk edit on a DocType with a workflow unless its List View Settings record
has allow_edit. Only that flag is set, so column choices on an existing record are kept.
"""

import frappe

LIST_VIEWS = ("Candidate Country Process", "Arrival and Deployment")


def execute():
	for doctype in LIST_VIEWS:
		if frappe.db.exists("List View Settings", doctype):
			frappe.db.set_value("List View Settings", doctype, "allow_edit", 1)
		else:
			frappe.get_doc({"doctype": "List View Settings", "name": doctype, "allow_edit": 1}).insert()
