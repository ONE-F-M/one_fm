import frappe
from one_fm.custom.assignment_rule.assignment_rule import get_assignment_rule_json_file, create_assignment_rule

def execute():
    create_assignment_rule(get_assignment_rule_json_file("roster_post_action_site_supervisor.json"))
    create_assignment_rule(get_assignment_rule_json_file("subcontract_staff_shortlist.json"))
    # create_assignment_rule(get_assignment_rule_json_file("roster_post_action_site_supervisor.json"))
    create_assignment_rule(get_assignment_rule_json_file("action_poc_check.json"))
    create_assignment_rule(get_assignment_rule_json_file("shift_permission_approver.json"))
    create_assignment_rule(get_assignment_rule_json_file("purchase_order_purchase_manager_action.json"))
