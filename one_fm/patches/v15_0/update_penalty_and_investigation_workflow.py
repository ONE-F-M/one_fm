import frappe
from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file

def execute():
    """Create or update Penalty & Investigation workflow."""
    workflow_data = get_workflow_json_file("penalty_and_investigation.json")
    if workflow_data:
        create_workflow(workflow_data)
        frappe.db.commit()
