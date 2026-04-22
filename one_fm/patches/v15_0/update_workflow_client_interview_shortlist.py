import frappe
from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow


def execute():
	"""
	Story 3: Update the Client Interview Shortlist workflow to add:
	- 'Completed' state (doc_status=1, allow_edit=Operations Supervisor)
	- 'Complete' transition: Approved → Completed (allowed: Operations Supervisor)
	- 'Cancel' transition from Completed → Cancelled (allowed: Operations Supervisor)
	"""
	create_workflow(get_workflow_json_file("client_interview_shortlist.json"))
