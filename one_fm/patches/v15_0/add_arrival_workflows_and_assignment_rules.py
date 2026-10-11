import frappe

from one_fm.setup.assignment_rule import create_assignment_rule, get_assignment_rule_json_file
from one_fm.setup.workflow import create_workflow, get_workflow_json_file

ASSIGNMENT_RULES = (
	"arrival_and_deployment_draft.json",
	"arrival_and_deployment_pending_onboarding.json",
	"arrival_acknowledgement_department.json",
)


def execute():
	"""Ship the Arrival Acknowledgement workflow and the arrival assignment rules."""
	create_workflow(get_workflow_json_file("arrival_acknowledgement.json"))
	for rule in ASSIGNMENT_RULES:
		create_assignment_rule(get_assignment_rule_json_file(rule))
	frappe.clear_cache(doctype="Arrival and Deployment")
	frappe.clear_cache(doctype="Arrival Acknowledgement")
