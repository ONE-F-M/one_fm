import frappe

from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file

# WI-003016: a Medical Appointment opened by a Preparation had no appointment date, no
# transport decision and no PRO yet, but the workflow's first state was Pending
# Supervisor, so a supervisor was assigned to act on a record with nothing to act on.
# The workflow now gains a Draft state ahead of Pending Supervisor and one action out
# of it, so the supervisor is only assigned once the record is filled in and moved on.
#
# This only re-applies the workflow definition. It does not move any existing Medical
# Appointment to Draft - records already in Pending Supervisor or any other state keep
# the state they are in today.
WORKFLOW = "Medical Appointment"
DRAFT = "Draft"
DRAFT_TRANSITION = (DRAFT, "Submit", "Pending Supervisor")


def execute():
	create_workflow(get_workflow_json_file("medical_appointment.json"))
	verify()


def verify():
	"""Checked after the fact - create_workflow logs its failures instead of raising, so it
	can report success having changed nothing."""
	workflow = frappe.get_doc("Workflow", WORKFLOW)

	if DRAFT not in {state.state for state in workflow.states}:
		frappe.throw(
			f"WI-003016: the {WORKFLOW} workflow has no {DRAFT} state - check the Error Log."
		)

	transitions = {(t.state, t.action, t.next_state) for t in workflow.transitions}
	if DRAFT_TRANSITION not in transitions:
		frappe.throw(
			f"WI-003016: {DRAFT_TRANSITION} is missing from the {WORKFLOW} workflow, which "
			f"would leave every appointment opened in {DRAFT} with no way out of it."
		)
