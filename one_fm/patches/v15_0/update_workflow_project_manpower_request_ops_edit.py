import frappe
from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow

def execute():
	print("=== Patch: Updating PMR workflow for Ops Edit in In Process state ===")
	workflow_data = get_workflow_json_file("project_manpower_request.json")
	create_workflow(workflow_data)
	print("Workflow reloaded successfully.")
