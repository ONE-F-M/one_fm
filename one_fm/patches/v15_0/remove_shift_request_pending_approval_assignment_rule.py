from one_fm.custom.assignment_rule.assignment_rule import delete_assignment_rule


def execute():
    delete_assignment_rule({"name": "Shift Request Pending Approval"})
