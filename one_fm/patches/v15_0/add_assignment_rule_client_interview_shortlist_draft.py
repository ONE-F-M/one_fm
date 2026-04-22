import frappe
from one_fm.setup.assignment_rule import create_assignment_rule, get_assignment_rule_json_file


def execute():
	"""Story 4: Create 'Client Interview Shortlist - Draft' assignment rule.
	Assigns the document owner (Operations Supervisor) when the record is in Draft state.
	Rule type: Based on Field (owner)."""

	OLD_ASSIGNMENT_RULES = [
	"Submit Client Interview Shortlist - Operations Supervisor",
	"Review & Approve Client Interview Shortlist - Operations Manager",
	"Finalize Client Interview Shortlist - Operations Supervisor",
	]

	for rule_name in OLD_ASSIGNMENT_RULES:
		if frappe.db.exists("Assignment Rule", rule_name):
			frappe.delete_doc("Assignment Rule", rule_name, ignore_permissions=True)

	create_assignment_rule(
		get_assignment_rule_json_file("client_interview_shortlist_draft.json")
	)
