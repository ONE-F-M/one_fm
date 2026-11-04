import frappe
from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file

def execute():
	"""Create or update Bank Account workflow with Inactive Account state."""
	workflow_data = get_workflow_json_file("bank_account.json")
	if workflow_data:
		create_workflow(workflow_data)
		# create_workflow logs failures instead of raising
		if not frappe.db.exists(
			"Workflow Transition",
			{"parent": "Bank Account", "action": "Set Inactive", "allowed": "Onboarding Officer"},
		):
			frappe.throw("Bank Account workflow was not updated, see Error Log")
		frappe.db.commit()
