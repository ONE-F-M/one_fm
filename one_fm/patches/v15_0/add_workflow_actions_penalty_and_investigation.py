import frappe
from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow_action_master

def execute():
	workflow = get_workflow_json_file("penalty_and_investigation.json")
	actions = list(set([transition["action"] for transition in workflow["transitions"]]))
	create_workflow_action_master(actions)
