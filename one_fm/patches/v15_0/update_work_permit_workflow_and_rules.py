"""WI-002497: the Work Permit workflow and the GR Operator's assignment rule.

The permit is the operator's from the moment it is saved. It was not: a Draft saved into
"Apply Online by PRO", a PRO step nobody takes - "Work Permit-PRO", the only rule that
assigned that state, has been disabled since WI-002182 - and the Apply action that moves
the permit on hung off it. So every permit passed through a state whose owner does not
exist, and the operator holding it was told nothing.

    Draft --Save--> Pending by GR Operator --Apply--> Pending GR Manager

"Pending By Operator" is renamed "Pending by GR Operator" in the same move, so the state
the permit comes back to after payment and the state it starts in are one state rather
than two spellings of the same idea.

Five states also carried an `update_value` with no `update_field` beside it. Frappe writes
nothing without the field, so each was a claim to set a field none of them named. Cleared,
as the BA site has them.

`Apply Online by PRO` itself is left on the workflow. Nothing routes into it any more, and
the disabled Work Permit-PRO rule still names it - the state is what that rule would come
back to if the PRO step is ever turned on.

## Records already in flight

41 permits hold "Apply Online by PRO". They move to "Pending by GR Operator", which is
where their Apply action now lives; left behind they would have no action at all.
"""

import frappe

from one_fm.custom.assignment_rule.assignment_rule import (
	create_assignment_rule,
	get_assignment_rule_json_file,
)
from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file

DOCTYPE = "Work Permit"
WORKFLOW = "Work Permit"

PENDING_GRO = "Pending by GR Operator"
RETIRED_STATE = "Pending By Operator"
BYPASSED_STATE = "Apply Online by PRO"

RULE_NAME = "Work Permit - GR Operator"
RULE_JSON = "work_permit_gr_operator.json"

EXPECTED_TRANSITIONS = (
	("Draft", "Save", PENDING_GRO),
	(PENDING_GRO, "Apply", "Pending GR Manager"),
	(PENDING_GRO, "Done", "Completed"),
	("Pending  For Payment", "Paid", PENDING_GRO),
)


def execute():
	create_workflow(get_workflow_json_file("work_permit.json"))
	move_records_in_flight()
	create_assignment_rule(get_assignment_rule_json_file(RULE_JSON), task_for(RULE_NAME))
	verify()


def task_for(name):
	"""The Process Task the rule already points at, kept across the rewrite.

	The link is a site's own - the ids differ between sites - so the fixture does not carry
	one, and a task-based rule whose task is blanked assigns nobody without saying so. This
	rule is Based on Field today, so it is normally None; asked for anyway because a site
	configured by hand may not be.
	"""
	return frappe.db.get_value("Assignment Rule", name, "custom_routine_task") or None


def move_records_in_flight():
	"""Put every permit where its remaining action lives.

	update_modified=False: the move is this patch's doing, and the GRD lists sort by
	modified.
	"""
	for old in (BYPASSED_STATE, RETIRED_STATE):
		frappe.db.set_value(
			DOCTYPE,
			{"workflow_state": old},
			"workflow_state",
			PENDING_GRO,
			update_modified=False,
		)


def verify():
	"""create_workflow and create_assignment_rule log their failures instead of raising."""
	workflow = frappe.get_doc("Workflow", WORKFLOW)

	states = {state.state for state in workflow.states}
	if PENDING_GRO not in states:
		frappe.throw(f"WI-002497: the {WORKFLOW} workflow has no {PENDING_GRO!r} state.")
	if RETIRED_STATE in states:
		frappe.throw(
			f"WI-002497: {RETIRED_STATE!r} is still a state, so two spellings describe the "
			"same step."
		)

	transitions = {(t.state, t.action, t.next_state) for t in workflow.transitions}
	missing = [t for t in EXPECTED_TRANSITIONS if t not in transitions]
	if missing:
		frappe.throw(
			f"WI-002497: the {WORKFLOW} workflow is missing {missing}. Check the Error Log - "
			"create_workflow swallows its failures."
		)

	reachable = {t.next_state for t in workflow.transitions}
	if BYPASSED_STATE in reachable:
		frappe.throw(
			f"WI-002497: something still routes into {BYPASSED_STATE!r}, the state with no "
			"owner that this story takes the permit off."
		)

	for old in (BYPASSED_STATE, RETIRED_STATE):
		stranded = frappe.db.count(DOCTYPE, {"workflow_state": old})
		if stranded:
			frappe.throw(f"WI-002497: {stranded} {DOCTYPE} records still hold {old!r}.")

	saved = frappe.db.get_value(
		"Assignment Rule", RULE_NAME, ["disabled", "rule", "field", "assign_condition"], as_dict=True
	)
	if not saved:
		frappe.throw(f"WI-002497: assignment rule {RULE_NAME!r} does not exist.")
	if saved.disabled or saved.rule != "Based on Field" or saved.field != "owner":
		frappe.throw(
			f"WI-002497: {RULE_NAME!r} is disabled={saved.disabled} {saved.rule!r} on "
			f"{saved.field!r}; it should be an enabled Based on Field rule on the owner."
		)
	if PENDING_GRO not in (saved.assign_condition or ""):
		frappe.throw(
			f"WI-002497: {RULE_NAME!r} does not fire at {PENDING_GRO!r}, which is where a "
			"permit now waits for its operator."
		)
