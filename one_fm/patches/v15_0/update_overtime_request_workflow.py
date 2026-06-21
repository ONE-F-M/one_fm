from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow


def execute():
	"""Update the Overtime Request workflow with new states and transitions."""
	create_workflow(get_workflow_json_file("overtime_request.json"))
