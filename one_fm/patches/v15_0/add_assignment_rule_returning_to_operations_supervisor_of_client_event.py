import frappe
from one_fm.custom.assignment_rule.assignment_rule import get_assignment_rule_json_file, create_assignment_rule, delete_assignment_rule

def execute():
    if frappe.db.exists("Assignment Rule", "Returning to Operations Supervisor of Client Event"):
        frappe.delete_doc("Assignment Rule", "Returning to Operations Supervisor of Client Event", ignore_permissions=True)
        
    assignment_rule_data = get_assignment_rule_json_file("returning_to_operations_supervisor_of_client_event.json")
    delete_assignment_rule(assignment_rule_data)
    create_assignment_rule(assignment_rule_data)
