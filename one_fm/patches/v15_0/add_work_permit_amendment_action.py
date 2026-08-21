import frappe

from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file

# WI-002108: PAM sends a permit back to be amended rather than rejecting it, and the
# workflow had no way to say so - the operator either accepted a permit that was wrong or
# rejected one that was only incomplete.
WORKFLOW = "Work Permit"
# The destination state was renamed to Pending GR Manager by WI-002097; the transition is
# the same one.
AMEND_TRANSITION = ("Pending By PAM", "Amend", "Pending GR Manager")


def execute():
	frappe.reload_doc("grd", "doctype", "work_permit")

	create_workflow(get_workflow_json_file("work_permit.json"))
	verify()


def verify():
	"""Checked after the fact - create_workflow logs its failures instead of raising."""
	workflow = frappe.get_doc("Workflow", WORKFLOW)

	transitions = {(t.state, t.action, t.next_state) for t in workflow.transitions}
	if AMEND_TRANSITION not in transitions:
		frappe.throw(
			f"WI-002108: {AMEND_TRANSITION} is missing from the {WORKFLOW} workflow - "
			"check the Error Log. Without it the Amendment No can never be incremented."
		)
