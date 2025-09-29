import frappe
from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow

def execute():
    create_workflow(get_workflow_json_file("erf.json"))
    create_workflow(get_workflow_json_file("leave_acknowledgement_form.json"))
    create_workflow(get_workflow_json_file("purchase_order.json"))
