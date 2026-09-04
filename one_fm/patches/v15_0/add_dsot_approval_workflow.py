import frappe

from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file

# WI-002283: an overtime schedule for somebody already working a basic shift that day is a
# double shift, and waits for a decision before it becomes a Shift Assignment.
#
# The states join the workflow Employee Schedule already has, because Frappe runs one
# workflow per doctype. Approving lands on Active rather than on a state of its own: only
# an Active schedule is picked up for a Shift Assignment, and only an Active one can later
# be suspended - a separate "Approved" state would have taken both away.
WORKFLOW_FILE = "employee_schedule.json"
WORKFLOW_NAME = "Employee Schedule Suspension"

PENDING_DSOT = "Pending DSOT Approval"
REJECTED = "Rejected"

# Warning for the wait, Danger for the refusal - the same reading the suspension states use.
STATE_STYLES = {PENDING_DSOT: "Warning", REJECTED: "Danger"}


def execute():
	frappe.reload_doc("one_fm", "doctype", "operation_settings")

	ensure_workflow_states()
	create_workflow(get_workflow_json_file(WORKFLOW_FILE))

	verify()


def ensure_workflow_states():
	"""A workflow cannot link to a state that has no master record, and Workflow State.style
	is mandatory on this site - create_workflow logs that failure instead of raising it, so
	the workflow would silently keep its old states."""
	for state, style in STATE_STYLES.items():
		if frappe.db.exists("Workflow State", state):
			continue
		frappe.get_doc({
			"doctype": "Workflow State",
			"workflow_state_name": state,
			"style": style,
		}).insert(ignore_permissions=True)


def verify():
	"""create_workflow logs its failures instead of raising them."""
	workflow = frappe.get_doc("Workflow", WORKFLOW_NAME)
	states = {state.state for state in workflow.states}

	for state in STATE_STYLES:
		if state not in states:
			frappe.throw(f"WI-002283: the Employee Schedule workflow has no {state!r} state.")

	decisions = {
		(t.action, t.next_state)
		for t in workflow.transitions if t.state == PENDING_DSOT
	}
	if ("Approve", "Active") not in decisions:
		frappe.throw(
			"WI-002283: approving a DSOT request does not reach Active, so the schedule "
			"would never be given a Shift Assignment."
		)
	if ("Reject", REJECTED) not in decisions:
		frappe.throw("WI-002283: a DSOT request cannot be rejected.")

	# The suspension flow this shares a workflow with has to survive intact.
	if ("Request Suspension", "Pending Suspension") not in {
		(t.action, t.next_state) for t in workflow.transitions if t.state == "Active"
	}:
		frappe.throw("WI-002283: the suspension flow lost its Request Suspension transition.")

	if not frappe.get_meta("Operation Settings").get_field("dsot_approver"):
		frappe.throw("WI-002283: Operation Settings has no DSOT Approver field.")

	print("WI-002283: DSOT approval added to the Employee Schedule workflow")
