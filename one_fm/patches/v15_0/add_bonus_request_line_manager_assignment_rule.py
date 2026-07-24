from one_fm.custom.assignment_rule.assignment_rule import (
	get_assignment_rule_json_file, create_assignment_rule
)


def execute():
	"""WI-001697: Create the "Bonus Request - Line Manager" assignment rule.

	Based-on-Field rule targeting reports_to_user, so a Bonus Request in the
	Pending Line Manager state is assigned to the requester's line manager.
	"""
	create_assignment_rule(
		get_assignment_rule_json_file("bonus_request_line_manager.json")
	)
