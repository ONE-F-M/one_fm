from one_fm.custom.assignment_rule.assignment_rule import (
	get_assignment_rule_json_file, create_assignment_rule, delete_assignment_rule
)

# add_resignation_v2_branch_routing installed the new workflow states (Pending
# Line Manager / T4 Admin / Cleaning Head Supervisor / Security Manager /
# Project Manager) but never created Assignment Rules for them -- so every one
# of those states landed with nobody assigned. This creates the missing ones
# and removes rules left over from the pre-v2 workflow that can no longer fire.
NEW_RULES = [
	"employee_resignation_pending_line_manager.json",
	"employee_resignation_pending_t4_admin.json",
	"employee_resignation_pending_janitorial_head_supervisor.json",
	"employee_resignation_pending_security_manager.json",
	"employee_resignation_pending_project_manager.json",
	"employee_resignation_withdrawal_pending_line_manager.json",
	"employee_resignation_withdrawal_pending_t4_admin.json",
	"employee_resignation_withdrawal_pending_janitorial_head_supervisor.json",
	"employee_resignation_withdrawal_pending_security_manager.json",
	"employee_resignation_withdrawal_pending_project_manager.json",
]

# Pre-v2 rules that either target a state/field the redesign deleted
# ("Pending Operations Manager", the operations_manager field) or duplicate a
# fixture-backed rule under an older naming convention.
STALE_RULES = [
	{"name": "Resignation - Pending Operations Manager"},
	{"name": "Employee Resignation - Pending Operations Manager"},
	{"name": "Employee Resignation Withdrawal - Pending Operations Manager"},
	# Duplicate of the fixture-backed "Employee Resignation - Pending Supervisor" --
	# both assign the same `supervisor` field on the same condition, risking
	# duplicate notification emails.
	{"name": "Resignation - Pending Supervisor"},
	# Assigns based on `owner` (whoever triggered the transition), which is
	# exactly the bug assign_employee_for_relieving_date_correction() in
	# employee_resignation.py was written to fix -- the two fight each other.
	{"name": "Resignation - Relieving Date Correction"},
]


def execute():
	for rule_file in NEW_RULES:
		create_assignment_rule(get_assignment_rule_json_file(rule_file))

	for rule in STALE_RULES:
		delete_assignment_rule(rule)
