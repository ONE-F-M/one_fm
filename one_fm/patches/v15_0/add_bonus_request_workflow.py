from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow, delete_workflow

def execute():
	"""Add Bonus Request workflow."""
	workflow_data = get_workflow_json_file("bonus_request.json")
	delete_workflow(workflow_data)
	create_workflow(workflow_data)
