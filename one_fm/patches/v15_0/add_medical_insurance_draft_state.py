import frappe

from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file

# WI-002098: an overseas hire's policy is paid for on the provider's portal before there is
# anything for the PRO to apply for, so the workflow gains a Draft state ahead of
# Apply Online by PRO and one action out of it.
WORKFLOW = "Medical Insurance"
DRAFT = "Draft"
DRAFT_TRANSITION = (DRAFT, "Submit", "Apply Online by PRO")


def execute():
	create_workflow(get_workflow_json_file("medical_insurance.json"))
	verify()


def verify():
	"""Checked after the fact - create_workflow logs its failures instead of raising, so it
	can report success having changed nothing."""
	workflow = frappe.get_doc("Workflow", WORKFLOW)

	if DRAFT not in {state.state for state in workflow.states}:
		frappe.throw(
			f"WI-002098: the {WORKFLOW} workflow has no {DRAFT} state - check the Error Log."
		)

	transitions = {(t.state, t.action, t.next_state) for t in workflow.transitions}
	if DRAFT_TRANSITION not in transitions:
		frappe.throw(
			f"WI-002098: {DRAFT_TRANSITION} is missing from the {WORKFLOW} workflow, which "
			f"would leave every policy opened in {DRAFT} with no way out of it."
		)
