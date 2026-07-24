import frappe
from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow


def execute():
	"""WI-001694: install the Employee Schedule suspension approval workflow.

	States: Active -> Pending Suspension -> (Approve) Suspended / (Reject) Active.
	Employee Availability is only changed to "Suspended" on approval.
	"""
	create_workflow(get_workflow_json_file("employee_schedule.json"))
	frappe.clear_cache(doctype="Employee Schedule")
