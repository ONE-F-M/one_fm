from one_fm.custom.workflow.workflow import create_workflow_state


def execute():
	# Set by the HR Enquiry Lifecycle process when HR escalates an enquiry to Legal.
	create_workflow_state([{"workflow_state_name": "Escalated to Legal", "style": "Warning"}])
