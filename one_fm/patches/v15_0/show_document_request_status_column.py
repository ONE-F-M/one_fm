import json

import frappe


def execute():
	"""Add the status column to saved Document Request list settings, which otherwise drop it."""
	fields = frappe.db.get_value("List View Settings", "Document Request", "fields")
	if not fields:
		return
	columns = json.loads(fields)
	if any(d.get("fieldname") == "status_field" for d in columns):
		return
	columns.insert(1, {"fieldname": "status_field", "label": "Status"})
	frappe.db.set_value("List View Settings", "Document Request", "fields", json.dumps(columns))
