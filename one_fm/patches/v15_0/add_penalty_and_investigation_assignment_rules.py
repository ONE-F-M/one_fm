import frappe
from one_fm.custom.assignment_rule.assignment_rule import (
	get_assignment_rule_json_file, create_assignment_rule
)

# One rule per waiting state of the workflow added in WI-001796.
ASSIGNMENT_RULES = [
	"penalty_and_investigation_hr_administrator.json",
	"penalty_and_investigation_legal_manager.json",
	"penalty_and_investigation_general_manager.json",
]


def execute():
	"""Create the Penalty And Investigation assignment rules (WI-001798).

	Assignment rules are only created by the installer, so an existing site needs
	them applied here.
	"""
	for rule_file in ASSIGNMENT_RULES:
		create_assignment_rule(get_assignment_rule_json_file(rule_file))

	# create_assignment_rule logs its failures instead of raising, so confirm the
	# result rather than trusting it.
	for rule_file in ASSIGNMENT_RULES:
		name = get_assignment_rule_json_file(rule_file)["name"]
		if not frappe.db.exists("Assignment Rule", name):
			frappe.log_error(
				title="Penalty Assignment Rule Not Applied",
				message=f"Assignment Rule '{name}' was not created. Check the Error Log "
				"for 'Assignment Rule Save Error'.",
			)
