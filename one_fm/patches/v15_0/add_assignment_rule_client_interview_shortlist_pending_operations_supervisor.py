from one_fm.setup.assignment_rule import create_assignment_rule, get_assignment_rule_json_file


def execute():
	"""Story 4: Create 'Client Interview Shortlist - Pending Operations Supervisor' assignment rule.
	Assigns the document owner (Operations Supervisor) when the record is Pending Operations Supervisor.
	Rule type: Based on Field (owner)."""
	create_assignment_rule(
		get_assignment_rule_json_file("client_interview_shortlist_pending_operations_supervisor.json")
	)
