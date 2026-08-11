import frappe

from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file

# WI-001827: PAM's refusal is one step now, so the state it used to park in has no
# transitions left. Anything still sitting there would have no action at all.
STRANDED_STATE = "Reason of Rejection"
STRANDED_LANDS_IN = "Rejected"


def execute():
	"""Collapse the PAM rejection to a single step, without stranding anything."""
	rescue_stranded_documents()
	create_workflow(get_workflow_json_file("work_permit.json"))
	verify()


def rescue_stranded_documents():
	"""Move permits out of the state that is about to have no way out.

	Before the workflow is applied, so there is never a moment where a permit holds a
	state with no transitions. The ones in it were rejections halfway through the old
	two-step flow - which is exactly what Rejected now means in one step.
	"""
	stranded = frappe.get_all(
		"Work Permit", filters={"workflow_state": STRANDED_STATE}, pluck="name"
	)
	if not stranded:
		return

	for name in stranded:
		# update_modified stays off: the state was retired underneath these permits,
		# which is not an edit by whoever ran migrate.
		frappe.db.set_value(
			"Work Permit", name, "workflow_state", STRANDED_LANDS_IN, update_modified=False
		)

	print(f"WI-001827: moved {len(stranded)} Work Permit(s) out of {STRANDED_STATE!r}")


def verify():
	"""create_workflow logs failures instead of raising, so check it actually applied."""
	transitions = {
		(t.state, t.action, t.next_state)
		for t in frappe.get_doc("Workflow", "Work Permit").transitions
	}

	if ("Pending By PAM", "Reject", "Rejected") not in transitions:
		frappe.throw("WI-001827: the one-step PAM rejection is not on the Work Permit workflow.")

	still_routed = [t for t in transitions if STRANDED_STATE in (t[0], t[2])]
	if still_routed:
		frappe.throw(f"WI-001827: {STRANDED_STATE!r} still has transitions: {still_routed}")

	left_behind = frappe.db.count("Work Permit", {"workflow_state": STRANDED_STATE})
	if left_behind:
		frappe.throw(f"WI-001827: {left_behind} Work Permit(s) left in {STRANDED_STATE!r}.")
