import frappe
from one_fm.setup.assignment_rule import create_assignment_rule, get_assignment_rule_json_file

def execute():
    assignment_rule_data = get_assignment_rule_json_file("subcontract_staff_attendance_subcontractor.json")
    
    create_assignment_rule(assignment_rule_data)
