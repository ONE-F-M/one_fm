from one_fm.custom.assignment_rule.assignment_rule import (
	get_assignment_rule_json_file, create_assignment_rule
)


def execute():
	"""Create assignment rule for Process Change Request - Business Analyst."""
	create_assignment_rule(
		get_assignment_rule_json_file("action_process_change_request_business_analyst.json")
	)
