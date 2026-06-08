import frappe
from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow

def execute():
	# Reload PMR workflow in the database to apply Operation Admin roles
	workflow_data = get_workflow_json_file("project_manpower_request.json")
	create_workflow(workflow_data)
