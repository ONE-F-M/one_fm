import frappe
from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file

def execute():
	"""Create or update Bank Account workflow with Inactive Account state."""
	workflow_data = get_workflow_json_file("bank_account.json")
	if workflow_data:
		create_workflow(workflow_data)
		frappe.db.commit()
