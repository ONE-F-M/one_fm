import frappe

from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file

WORKFLOW_NAME = "Employee Schedule Suspension"

# WI-001694 names four approver roles for the Approve/Reject transitions. Every role a
# Workflow Transition references must exist, or the whole Workflow insert fails link
# validation - and create_workflow() swallows that into an Error Log, so migrate reports
# success while nothing is installed. "Operations Admin" does not exist on every site, so
# it is created here (empty, for an administrator to assign users to).


def execute():
	"""WI-001694: install the Employee Schedule suspension approval workflow.

	States: Active -> Pending Suspension -> (Approve) Suspended / (Reject) Active.
	Employee Availability is only changed to "Suspended" on approval.
	"""

	create_workflow(get_workflow_json_file("employee_schedule.json"))
	frappe.clear_cache(doctype="Employee Schedule")
