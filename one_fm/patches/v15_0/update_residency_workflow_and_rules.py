"""WI-002495: the Residency (MOI) workflow, its PRO field, and the two rules that assign it.

The workflow the site has is one state wide: everything lands in "Apply Online by PRO" and
leaves it Completed. That single state is doing the work of three - the draft nobody has
routed yet, the PRO's turn, and the GR Operator's - so nothing on a Residency says who is
holding it.

What replaces it:

    Draft --Assign PRO--------> Pending by PRO --Submit to GR Operator--\\
         \\--Process Online----> Pending by GR Operator <----------------/
                                        |
                                        \\--Done--> Completed

`pro_user` is new on the DocType, filtered to users who hold the PRO role, because
"Residency - PRO" selects its assignee from it - a Based on Field rule pointed at a field
that does not exist assigns nobody and says nothing about it.

## The 810 records already in flight

They hold "Apply Online by PRO", which the new workflow does not have. They are moved to
**Pending by GR Operator**, not to Pending by PRO: the only action those records have today
is Done → Completed, taken by the GR Operator, and Pending by GR Operator is the state that
still offers it. Sending them to Pending by PRO would hand 810 live applications to a PRO
who is not named on any of them - `pro_user` is blank on every one - and the only way out of
that state is an action only the PRO can take.

## One deviation from the BA site's own configuration

The BA site's "Residency - PRO" rule assigns on `workflow_state == "Apply Online by PRO"`,
a state its own MOI workflow no longer has. Copied verbatim the rule would never fire once.
It assigns on "Pending by PRO" here, which is what the rule is for.
"""

import frappe

from one_fm.custom.assignment_rule.assignment_rule import (
	create_assignment_rule,
	get_assignment_rule_json_file,
)
from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file

DOCTYPE = "Residency"
WORKFLOW = "MOI"
OLD_STATE = "Apply Online by PRO"
IN_FLIGHT_STATE = "Pending by GR Operator"

RULES = {
	"Residency - GR Operator": "residency_gr_operator.json",
	"Residency - PRO": "residency_pro.json",
}

EXPECTED_STATES = ("Draft", "Pending by PRO", IN_FLIGHT_STATE, "Completed", "Cancelled")

EXPECTED_TRANSITIONS = (
	("Draft", "Assign PRO", "Pending by PRO"),
	("Draft", "Process Online", IN_FLIGHT_STATE),
	("Pending by PRO", "Submit to GR Operator", IN_FLIGHT_STATE),
	(IN_FLIGHT_STATE, "Done", "Completed"),
)


def execute():
	create_workflow(get_workflow_json_file("moi.json"))
	move_records_in_flight()

	for rule_file in RULES.values():
		create_assignment_rule(get_assignment_rule_json_file(rule_file))

	verify()


def move_records_in_flight():
	"""Put the records holding the retired state where their remaining action lives.

	update_modified=False: the move is this patch's doing, and the GRD lists sort by
	modified - 810 applications jumping to the top would read as 810 things that just
	happened.
	"""
	frappe.db.set_value(
		DOCTYPE,
		{"workflow_state": OLD_STATE},
		"workflow_state",
		IN_FLIGHT_STATE,
		update_modified=False,
	)


def verify():
	"""create_workflow and create_assignment_rule log their failures instead of raising."""
	workflow = frappe.get_doc("Workflow", WORKFLOW)

	states = {state.state for state in workflow.states}
	missing_states = [state for state in EXPECTED_STATES if state not in states]
	if missing_states:
		frappe.throw(f"WI-002495: the {WORKFLOW} workflow is missing states {missing_states}.")

	if OLD_STATE in states:
		frappe.throw(
			f"WI-002495: {OLD_STATE!r} is still a state on {WORKFLOW}, so the old single-state "
			"flow is still reachable."
		)

	transitions = {(t.state, t.action, t.next_state) for t in workflow.transitions}
	missing_transitions = [t for t in EXPECTED_TRANSITIONS if t not in transitions]
	if missing_transitions:
		frappe.throw(
			f"WI-002495: the {WORKFLOW} workflow is missing {missing_transitions}. Check the "
			"Error Log - create_workflow swallows its failures."
		)

	stranded = frappe.db.count(DOCTYPE, {"workflow_state": OLD_STATE})
	if stranded:
		frappe.throw(f"WI-002495: {stranded} {DOCTYPE} records still hold {OLD_STATE!r}.")

	if not frappe.get_meta(DOCTYPE).get_field("pro_user"):
		frappe.throw(
			"WI-002495: Residency has no pro_user field, so 'Residency - PRO' would assign "
			"nobody."
		)

	for rule_name in RULES:
		saved = frappe.db.get_value(
			"Assignment Rule", rule_name, ["disabled", "rule", "field"], as_dict=True
		)
		if not saved:
			frappe.throw(f"WI-002495: assignment rule {rule_name!r} does not exist.")
		if saved.disabled:
			frappe.throw(f"WI-002495: {rule_name!r} is disabled.")
		if saved.rule != "Based on Field" or not saved.field:
			frappe.throw(
				f"WI-002495: {rule_name!r} is {saved.rule!r} on field {saved.field!r}, so it "
				"selects its assignee from nothing."
			)
