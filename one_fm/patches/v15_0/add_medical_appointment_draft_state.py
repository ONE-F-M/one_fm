import frappe

from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file
from one_fm.custom.assignment_rule.assignment_rule import (
	create_assignment_rule,
	get_assignment_rule_json_file,
)

# WI-002886: a Medical Appointment auto-created from a Preparation record now opens in
# "Draft" rather than "Pending Supervisor" - the appointment date, transportation and PRO
# are not facts the Preparation holds, so the Government Relations Operator fills them in
# before the appointment is handed to the supervisor. The workflow gains the Draft state
# and the transition out of it, and a new Assignment Rule routes a Draft appointment to the
# Government Relations Operator the same way the existing rules route the later states.
WORKFLOW = "Medical Appointment"
DRAFT = "Draft"
DRAFT_TRANSITION = (DRAFT, "Submit to Supervisor", "Pending Supervisor")


def execute():
	create_workflow(get_workflow_json_file("medical_appointment.json"))
	create_assignment_rule(
		get_assignment_rule_json_file("action_medical_appointment_gr_operator_draft.json")
	)
	verify()


def verify():
	"""Checked after the fact - create_workflow logs its failures instead of raising, so it
	can report success having changed nothing."""
	workflow = frappe.get_doc("Workflow", WORKFLOW)

	if DRAFT not in {state.state for state in workflow.states}:
		frappe.throw(
			f"WI-002886: the {WORKFLOW} workflow has no {DRAFT} state - check the Error Log."
		)

	transitions = {(t.state, t.action, t.next_state) for t in workflow.transitions}
	if DRAFT_TRANSITION not in transitions:
		frappe.throw(
			f"WI-002886: {DRAFT_TRANSITION} is missing from the {WORKFLOW} workflow, which "
			f"would leave every appointment opened in {DRAFT} with no way out of it."
		)

	if not frappe.db.exists(
		"Assignment Rule", "Action Medical Appointment - GR Operator (Draft)"
	):
		frappe.throw(
			f"WI-002886: the Draft Assignment Rule for {WORKFLOW} was not created - check "
			"the Error Log."
		)
