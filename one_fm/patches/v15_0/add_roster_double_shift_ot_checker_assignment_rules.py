from one_fm.custom.assignment_rule.assignment_rule import (
	get_assignment_rule_json_file, create_assignment_rule
)


def execute():
	"""WI-001689: assignment rules for Roster Double Shift OT Checker.

	Site Supervisor (priority 1, Based-on-Field site_supervisor_user) takes
	precedence; falls through to Project Manager (priority 0,
	project_manager_user) when the site supervisor is not set.
	"""
	for fname in (
		"roster_double_shift_ot_checker_site_supervisor.json",
		"roster_double_shift_ot_checker_project_manager.json",
	):
		create_assignment_rule(get_assignment_rule_json_file(fname))
