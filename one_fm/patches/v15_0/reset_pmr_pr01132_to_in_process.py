import frappe

PMR = "Project Manpower Request"
NAME = "PR01132"


def execute():
	"""Reopen PR01132: pull it out of Completed back to the draft state In Process.

	"In Process" is a doc_status 0 state in the Project Manpower Request workflow
	(only "Completed" is doc_status 1), so docstatus 0 + In Process is a valid
	combination and the workflow can drive the document forward again.

	Child rows are reset too - Frappe refuses to save a draft parent whose child
	rows are still submitted.
	"""
	if not frappe.db.exists(PMR, {"name": NAME, "docstatus": 1, "workflow_state": "Completed"}):
		return

	frappe.db.set_value(PMR, NAME, {"docstatus": 0, "workflow_state": "In Process"}, update_modified=False)

	for df in frappe.get_meta(PMR).get_table_fields():
		frappe.db.set_value(df.options, {"parent": NAME, "parenttype": PMR}, "docstatus", 0, update_modified=False)
