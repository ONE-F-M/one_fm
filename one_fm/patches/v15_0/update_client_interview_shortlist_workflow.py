import frappe
from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file


def execute():
	"""Story 2: Update Client Interview Shortlist workflow to add:
	- custom_confirm_transition on Submit action (Pending Operations Supervisor → Completed)
	- Confirmation message: 'Are you sure you want to submit this Client Interview Shortlist?
	  Please check the Attendance and Selection checkbox.'
	- Rejected state style changed from Inverse to Primary
	"""
	workflow_data = get_workflow_json_file("client_interview_shortlist.json")
	if workflow_data:
		create_workflow(workflow_data)
		frappe.db.commit()
