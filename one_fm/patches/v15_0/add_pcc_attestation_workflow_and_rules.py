import frappe

from one_fm.custom.assignment_rule.assignment_rule import (
	create_assignment_rule,
	get_assignment_rule_json_file,
)
from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file

# WI-002029: the PCC Attestation workflow and the two rules that put each state on the right
# desk.
WORKFLOW = "PCC Attestation"
RULES = ("PCC Attestation-GRO", "PCC Attestation-PRO")
RULE_FILES = ("pcc_attestation_gro.json", "pcc_attestation_pro.json")

# Verified after the fact because create_workflow and create_assignment_rule both log their
# failures to the Error Log instead of raising, so either can report success having changed
# nothing.
EXPECTED_STATES = (
	"Draft",
	"Pending Embassy",
	"Pending MOFA",
	"Pending Translation",
	"Pending GR Operator",
	"On Hold",
	"Completed",
	"Cancelled",
)

# Every conditioned transition, because in each case the condition is the whole of its
# behaviour: the four Assign PRO transitions differ only in where they lead, and the two ways
# out of Pending Embassy differ only in whether MOFA applies. A condition lost in transit
# would leave the engine taking whichever it matched first and routing every record the same
# way - which is exactly what happened before WI-002025's master data forced the fourth path.
CONDITIONED_TRANSITIONS = {
	("Draft", "Assign PRO", "Pending Embassy"): 'doc.type == "Attestation" and doc.embassy_attestation_required',
	("Draft", "Assign PRO", "Pending MOFA"): 'doc.type == "Attestation" and not doc.embassy_attestation_required and doc.mofa_attestation_required',
	("Draft", "Assign PRO", "Pending Translation"): 'doc.type == "Translation" or (doc.type == "Attestation" and not doc.embassy_attestation_required and not doc.mofa_attestation_required and doc.translation_required)',
	("Draft", "Assign PRO", "Pending GR Operator"): 'doc.type == "Attestation" and not doc.embassy_attestation_required and not doc.mofa_attestation_required and not doc.translation_required',
	("Pending Embassy", "Submit MOFA Receipt", "Pending MOFA"): 'doc.mofa_attestation_required',
	("Pending Embassy", "Submit", "Pending GR Operator"): 'not doc.mofa_attestation_required',
}


def execute():
	frappe.reload_doc("grd", "doctype", "pcc_attestation")

	create_workflow(get_workflow_json_file("pcc_attestation.json"))
	verify_workflow()

	for rule_file in RULE_FILES:
		create_assignment_rule(get_assignment_rule_json_file(rule_file))
	verify_rules()


def verify_workflow():
	if not frappe.db.exists("Workflow", WORKFLOW):
		frappe.throw(
			f"WI-002029: the {WORKFLOW} workflow was not created. create_workflow swallows its "
			"failures - check the Error Log."
		)

	workflow = frappe.get_doc("Workflow", WORKFLOW)

	states = {state.state for state in workflow.states}
	missing_states = [state for state in EXPECTED_STATES if state not in states]

	transitions = {(t.state, t.action, t.next_state): (t.condition or "") for t in workflow.transitions}
	wrong_conditions = [
		key
		for key, condition in CONDITIONED_TRANSITIONS.items()
		if transitions.get(key) != condition
	]

	if missing_states or wrong_conditions:
		frappe.throw(
			f"WI-002029: the {WORKFLOW} workflow is incomplete. "
			f"Missing states: {missing_states or 'none'}. "
			f"Transitions with a missing or wrong condition: {wrong_conditions or 'none'}. "
			"An Assign PRO transition without its condition routes every record the same way."
		)


def verify_rules():
	missing = [rule for rule in RULES if not frappe.db.exists("Assignment Rule", rule)]
	if missing:
		frappe.throw(
			f"WI-002029: {missing} were not created - create_assignment_rule also logs its "
			"failures instead of raising, so check the Error Log."
		)
