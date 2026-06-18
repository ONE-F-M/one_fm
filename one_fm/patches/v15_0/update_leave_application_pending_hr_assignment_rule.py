import frappe
from one_fm.custom.assignment_rule.assignment_rule import (
	get_assignment_rule_json_file, create_assignment_rule
)

def execute():
	"""Update Leave Application - Pending HR assignment rule.

	Move close_condition to unassign_condition to prevent it from closing
	ToDos created by other assignment rules (e.g. Leave Application - Approved).

	close_condition runs in Phase 3 (after new assignments are created) and
	closes ALL open ToDos for the document. unassign_condition runs in Phase 1
	(before new assignments) and only affects assignments belonging to this rule.
	"""
	create_assignment_rule(get_assignment_rule_json_file("leave_application_pending_hr.json"))
