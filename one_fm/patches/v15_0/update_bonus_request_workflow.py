import frappe
from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow


def execute():
	"""Update the Bonus Request workflow.

	Adds the "Pending General Manager" approval step, renames the pre-payroll
	state from "Approved" to "Pending Payroll Officer", and adds the extra
	Reject / Cancel transitions and role-specific document states.
	"""
	create_workflow(get_workflow_json_file("bonus_request.json"))
	frappe.clear_cache(doctype="Bonus Request")
