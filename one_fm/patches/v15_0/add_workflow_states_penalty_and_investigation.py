import frappe
from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow_state

def execute():
	workflow = get_workflow_json_file("penalty_and_investigation.json")
	state_values = [{"workflow_state_name": state["state"], "style": state.get("style")} for state in workflow["states"]]
	create_workflow_state(state_values)
