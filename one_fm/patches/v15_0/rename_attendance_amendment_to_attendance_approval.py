"""Rename Attendance Amendment and its two child doctypes to Attendance Approval.

Must run pre_model_sync: if the doctype sync ran first it would create empty
Attendance Approval tables and the rename would fail on a name that exists.

rename_doc repoints Link/Table options, parenttype, Workflow, Assignment Rule,
Print Format, Version, ToDo, Comment, Custom Field and Property Setter rows.
Record names (Workflow, Assignment Rules, Print Formats) are left unchanged.
"""

import frappe

RENAMES = (
	("Attendance Amendment", "Attendance Approval"),
	("Attendance Amendment Item", "Attendance Approval Item"),
	("Attendance Amendment OT Item", "Attendance Approval OT Item"),
)


def execute():
	pending = [
		(old, new)
		for old, new in RENAMES
		if frappe.db.exists("DocType", old) and not frappe.db.exists("DocType", new)
	]
	if not pending:
		return

	# With developer_mode on, renaming a child re-saves the parent DocType, which
	# exports the DB definition over the code JSON and bumps its modified.
	developer_mode = frappe.local.conf.get("developer_mode")
	frappe.local.conf.developer_mode = 0
	try:
		for old, new in pending:
			frappe.rename_doc("DocType", old, new, force=True, show_alert=False)
	finally:
		frappe.local.conf.developer_mode = developer_mode

	frappe.db.set_value(
		"Custom Field",
		{"dt": "Sales Invoice", "fieldname": "custom_attendance_amendment"},
		"label",
		"Attendance Approval",
		update_modified=False,
	)
	frappe.db.commit()
