import frappe

from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file

# WI-001974: the previous employer's answer is a workflow decision now. "Informed
# Previous Company" only ever moved the permit forward, so a refusal had nowhere to go;
# it becomes Approve, and Reject lands in Rejected.
RENAMED_ACTIONS = {"Informed Previous Company": "Approve"}


def execute():
	"""Bring the Work Permit workflow's previous-company branch up to the BA site."""
	create_workflow(get_workflow_json_file("work_permit.json"))
	verify()


def verify():
	"""create_workflow logs failures instead of raising, so check it actually applied."""
	transitions = {
		(t.state, t.action, t.next_state)
		for t in frappe.get_doc("Workflow", "Work Permit").transitions
	}

	expected = {
		("Pending By Previous Company", "Approve", "Pending By PAM"),
		("Pending By Previous Company", "Reject", "Rejected"),
	}
	missing = expected - transitions

	if missing:
		frappe.throw(f"WI-001974: the Work Permit workflow was not applied. Missing: {missing}")

	for old_action in RENAMED_ACTIONS:
		if any(t[1] == old_action for t in transitions):
			frappe.throw(f"WI-001974: {old_action!r} is still on the Work Permit workflow.")
