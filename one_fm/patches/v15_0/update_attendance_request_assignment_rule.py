from one_fm.setup.assignment_rule import create_assignment_rule, get_assignment_rule_json_file, delete_assignment_rule

def execute():
    attendance_request_rule = get_assignment_rule_json_file("attendance_request_approval.json")
    delete_assignment_rule(attendance_request_rule)
    create_assignment_rule(attendance_request_rule)
