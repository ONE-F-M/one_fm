import frappe
from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow, delete_workflow

def execute():
    workflow_data = get_workflow_json_file("client_event.json")
    delete_workflow(workflow_data)
    create_workflow(workflow_data)
