import frappe
from one_fm.setup.assignment_rule import create_assignment_rule, get_assignment_rule_json_file
from one_fm.setup.workflow import create_workflow, get_workflow_json_file

def execute():
    create_assignment_rule(get_assignment_rule_json_file("action_fingerprint_appointment_pro.json"))
    create_workflow(get_workflow_json_file("fingerprint_appointment.json"))
