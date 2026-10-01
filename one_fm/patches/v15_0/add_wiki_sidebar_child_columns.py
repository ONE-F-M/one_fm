"""Give the Wiki Sidebar table the child-table columns Frappe only adds when it creates a table.

A table made while Wiki Sidebar was a standalone doctype has no parent, parentfield or parenttype,
and deleting any Wiki Page then fails: the link check reads `tabWiki Sidebar`.parent.
"""

import frappe
from frappe.database.schema import add_column

CHILD_COLUMNS = ("parent", "parentfield", "parenttype")


def execute():
	if not frappe.db.table_exists("Wiki Sidebar"):
		return
	for column in CHILD_COLUMNS:
		if not frappe.db.has_column("Wiki Sidebar", column):
			add_column("Wiki Sidebar", column, "Data")
	frappe.db.add_index("Wiki Sidebar", ["parent"], index_name="parent")
