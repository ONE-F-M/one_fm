import frappe
from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow

def execute():
	# Reload/update Project Manpower Request workflow with the new roles and transitions
	workflow_data = get_workflow_json_file("project_manpower_request.json")
	create_workflow(workflow_data)
