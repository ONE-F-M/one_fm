import frappe
from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow
from one_fm.one_fm.utils import create_role_if_not_exists

def execute():
    create_role_if_not_exists(["PRO"])
    create_workflow(get_workflow_json_file("medical_appointment.json"))