from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow
from one_fm.custom.assignment_rule.assignment_rule import (
	get_assignment_rule_json_file, create_assignment_rule, delete_assignment_rule
)

# create_employee_resignation_date_adjustment_workflow installed a Workflow
# with a "Pending Operations Manager" step, but the operations_manager field
# was later deleted from this doctype (alongside Resignation and Withdrawal),
# leaving that state permanently unreachable-by-anyone. The doctype/python
# side was already updated in parallel to carry the same T4 branch actors as
# Resignation/Withdrawal (t4_admin, cleaning_head_supervisor,
# security_manager, project_manager -- see set_approver() in
# employee_resignation_date_adjustment.py, which already fetches all of
# these from the parent Employee Resignation), and the workflow fixture on
# disk was updated to match -- it just was never pushed live, since the
# original patch only creates the Workflow once and never re-applies it.
# This pushes the fixture live and adds the Assignment Rules its new states
# need, exactly as was done for Resignation and Withdrawal.

NEW_RULES = [
	"employee_resignation_date_adjustment_pending_t4_admin.json",
	"employee_resignation_date_adjustment_pending_janitorial_head_supervisor.json",
	"employee_resignation_date_adjustment_pending_security_manager.json",
	"employee_resignation_date_adjustment_pending_project_manager.json",
]

STALE_RULES = [
	{"name": "Employee Resignation Date Adjustment - Pending Operations Manager"},
]


def execute():
	create_workflow(get_workflow_json_file("employee_resignation_date_adjustment.json"))

	for rule_file in NEW_RULES:
		create_assignment_rule(get_assignment_rule_json_file(rule_file))

	for rule in STALE_RULES:
		delete_assignment_rule(rule)
