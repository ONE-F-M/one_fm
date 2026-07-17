import frappe
from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow


def execute():
	"""Update the Leave Application workflow to trigger DSS on confirmation.

	Flags the "Pending Confirmation -> Confirm -> Approved" transition with
	require_digital_signature so that confirming a leave from the Pending
	Confirmation state triggers the Digital Signature Service (DSS)
	acknowledgement before the transition is applied.
	"""
	create_workflow(get_workflow_json_file("leave_application.json"))
	frappe.clear_cache(doctype="Leave Application")
