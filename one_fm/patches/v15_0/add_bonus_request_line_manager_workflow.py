import frappe
from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow


def execute():
	"""WI-001697: Add the "Pending Line Manager" approval step to the Bonus Request workflow.

	Reinstalls the workflow from JSON: "Submit for Review" now routes Draft ->
	Pending Line Manager, which approves into the existing Pending HR Manager chain.
	"""
	create_workflow(get_workflow_json_file("bonus_request.json"))
	frappe.clear_cache(doctype="Bonus Request")
