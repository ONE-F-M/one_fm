import frappe


def execute():
	"""
	Add Custom DocPerm context fields to the Version doctype.

	These fields are only visible when ref_doctype == 'Custom DocPerm' and
	surface the DocType, Role, Permission Level, and If Owner values from the
	permission rule that was changed — giving full audit context without having
	to open the Custom DocPerm record (which may have been deleted on reset).
	"""

	fields = [
		{
			"fieldname": "perm_section",
			"fieldtype": "Section Break",
			"label": "Permission Details",
			"depends_on": "eval:doc.ref_doctype == 'Custom DocPerm'",
			"insert_after": "docname",
		},
		{
			"fieldname": "perm_doctype",
			"fieldtype": "Link",
			"label": "DocType",
			"options": "DocType",
			"read_only": 1,
			"in_list_view": 0,
			"depends_on": "eval:doc.ref_doctype == 'Custom DocPerm'",
			"insert_after": "perm_section",
		},
		{
			"fieldname": "perm_column_break",
			"fieldtype": "Column Break",
			"insert_after": "perm_doctype",
		},
		{
			"fieldname": "perm_role",
			"fieldtype": "Link",
			"label": "Role",
			"options": "Role",
			"read_only": 1,
			"depends_on": "eval:doc.ref_doctype == 'Custom DocPerm'",
			"insert_after": "perm_column_break",
		},
		{
			"fieldname": "perm_column_break_2",
			"fieldtype": "Column Break",
			"insert_after": "perm_role",
		},
		{
			"fieldname": "perm_level",
			"fieldtype": "Int",
			"label": "Permission Level",
			"read_only": 1,
			"depends_on": "eval:doc.ref_doctype == 'Custom DocPerm'",
			"insert_after": "perm_column_break_2",
		},
		{
			"fieldname": "perm_column_break_3",
			"fieldtype": "Column Break",
			"insert_after": "perm_level",
		},
		{
			"fieldname": "perm_if_owner",
			"fieldtype": "Check",
			"label": "If Owner",
			"read_only": 1,
			"depends_on": "eval:doc.ref_doctype == 'Custom DocPerm'",
			"insert_after": "perm_column_break_3",
		},
	]

	for field in fields:
		if frappe.db.exists("Custom Field", {"dt": "Version", "fieldname": field["fieldname"]}):
			continue

		frappe.get_doc(
			{
				"doctype": "Custom Field",
				"dt": "Version",
				**field,
			}
		).insert(ignore_permissions=True)

	frappe.db.commit()
