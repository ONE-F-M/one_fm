import frappe
from one_fm.setup.workflow import create_workflow
from one_fm.custom.workflow.workflow import get_workflow_json_file

def execute():
    workflow_data = get_workflow_json_file("subcontractor_contracts.json")
    create_workflow(workflow_data)
