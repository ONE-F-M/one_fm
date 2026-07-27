import frappe
from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow


def execute():
	"""
	Re-sync the Employee Resignation workflow from its JSON definition.

	PR #6393 added a Draft state and corrected transitions to
	one_fm/custom/workflow/employee_resignation.json, but any site that had
	already run update_pmr_and_resignation_workflow_permissions (2026-06-30)
	does not pick up file changes automatically -- that patch only runs once.
	Without this re-sync, the Workflow record in the database keeps its old
	transitions (Pending Supervisor -> Pending Operations Manager directly),
	so new resignations skip the Pending Supervisor step entirely and fail
	the "specify Operations Manager" check at creation time.
	"""
	res_wf = get_workflow_json_file("employee_resignation.json")
	create_workflow(res_wf)
	frappe.clear_cache(doctype="Employee Resignation")
