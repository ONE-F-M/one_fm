from one_fm.custom.assignment_rule.assignment_rule import (
	get_assignment_rule_json_file, create_assignment_rule
)

def execute():
	"""Create Assignment Rule for Subcontractor Exit - Project Manager (Based on Field)."""
	create_assignment_rule(
		get_assignment_rule_json_file("subcontractor_exit_project_manager.json")
	)
