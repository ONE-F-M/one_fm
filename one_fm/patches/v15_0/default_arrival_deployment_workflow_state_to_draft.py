import frappe


def execute():
	"""Default Arrival and Deployment's workflow_state to Draft.

	Processa sets Draft on a separate copy of the record during the insert, so the
	form gets back a record with no state and shows the status field ("Pending")
	until it is reloaded. The field is permlevel 1, so the controller cannot set it
	for users without that level; Frappe resets such fields to their default.
	"""
	if not frappe.db.exists("Custom Field", "Arrival and Deployment-workflow_state"):
		return

	frappe.db.set_value("Custom Field", "Arrival and Deployment-workflow_state", "default", "Draft")
	frappe.clear_cache(doctype="Arrival and Deployment")
