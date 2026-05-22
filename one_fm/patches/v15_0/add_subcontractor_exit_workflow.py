from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow

def execute():
	"""Add Subcontractor Exit workflow."""
	workflow_data = get_workflow_json_file("subcontractor_exit.json")
	create_workflow(workflow_data)
