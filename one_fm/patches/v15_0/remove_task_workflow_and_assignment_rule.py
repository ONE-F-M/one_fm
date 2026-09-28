import frappe


def execute():
	"""Remove the Task workflow and its "Confirm ERPNext Task" assignment rule.

	Both are retired; the workflow_state Custom Field on Task and the status
	field it writes are left untouched.
	"""
	if frappe.db.exists("Assignment Rule", "Confirm ERPNext Task"):
		frappe.delete_doc("Assignment Rule", "Confirm ERPNext Task", force=True, ignore_permissions=True)

	if frappe.db.exists("Workflow", "Task"):
		frappe.delete_doc("Workflow", "Task", force=True, ignore_permissions=True)

	actions = frappe.get_all("Workflow Action", filters={"reference_doctype": "Task"}, pluck="name")
	if actions:
		frappe.db.delete("Workflow Action Permitted Role", {"parent": ["in", actions]})
		frappe.db.delete("Workflow Action", {"name": ["in", actions]})

	frappe.clear_cache()
