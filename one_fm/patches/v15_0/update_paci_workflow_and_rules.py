"""WI-002496: the PACI workflow, its PRO field and its two assignment rules.

Three things, all of them about the PRO tier being half-built:

  - **the states are renamed.** "Pending GR Operator" is "Pending by GR Operator" and
    "Pending PRO" is "Pending by PRO", matching the BA site and the way every other GRD
    workflow on this site spells the same idea;
  - **the PRO gets the two update states of their own.** An address or a photo PACI
    rejects can be the PRO's to fix - they are the one holding the portal session - and
    there was no way to say so. The operator's own "Pending Address Update" and "Pending
    Photo Update" stay exactly as they are;
  - **the route to the PRO is the operator's to take.** Draft --> Pending by PRO was
    "Save" allowed to the PRO role, which no PRO can reach: a Draft PACI is the
    operator's, and the PRO has no reason to be in it. It is "Submit to PRO", allowed to
    the Government Relations Operator. `hand_to_pro` still writes the state directly for
    a PACI the system opens off a Preparation - there is no operator in that session
    either.

`pro_user` gains the PRO link filter and becomes mandatory in the three states the PRO
holds. A Based on Field rule whose field is blank assigns nobody and says nothing.

## Records already in flight

649 applications hold "Pending GR Operator" and 28 hold "Pending PRO". Both names are
gone, and a record holding a state the workflow does not have has no action at all, so
they are renamed here.
"""

import frappe

from one_fm.custom.assignment_rule.assignment_rule import (
	create_assignment_rule,
	get_assignment_rule_json_file,
)
from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file

DOCTYPE = "PACI"
WORKFLOW = "PACI"

RENAMED_STATES = {
	"Pending GR Operator": "Pending by GR Operator",
	"Pending PRO": "Pending by PRO",
}

PENDING_GRO = "Pending by GR Operator"
PENDING_PRO = "Pending by PRO"
ADDRESS_BY_PRO = "Pending Address Update by PRO"
PHOTO_BY_PRO = "Pending Photo Update by PRO"

RULES = {
	"Action PACI": "action_paci.json",
	"PACI-PRO": "paci_pro.json",
}

EXPECTED_TRANSITIONS = (
	("Draft", "Submit to PRO", PENDING_PRO),
	(PENDING_GRO, "Update Address By PRO", ADDRESS_BY_PRO),
	(PENDING_GRO, "Update Photo by PRO", PHOTO_BY_PRO),
	(ADDRESS_BY_PRO, "Address Updated", PENDING_GRO),
	(PHOTO_BY_PRO, "Photo Updated", PENDING_GRO),
)


def execute():
	create_workflow(get_workflow_json_file("paci.json"))
	rename_records_in_flight()

	for rule_file in RULES.values():
		create_assignment_rule(get_assignment_rule_json_file(rule_file), task_for(rule_file))

	verify()


def task_for(rule_file):
	"""The Process Task a rule already points at, kept across the rewrite.

	The link is a site's own - the ids differ between sites - so the fixture does not
	carry one. A task-based rule whose task is blanked assigns nobody, and says nothing
	about it. Both PACI rules are Based on Field today, so this is normally None; it is
	asked for anyway because a site that was configured by hand may not be.
	"""
	name = next(name for name, filename in RULES.items() if filename == rule_file)
	return frappe.db.get_value("Assignment Rule", name, "custom_routine_task") or None


def rename_records_in_flight():
	"""Move every record off a state name the workflow no longer has.

	update_modified=False: the rename is this patch's doing, and the GRD lists sort by
	modified - 677 applications jumping to the top would read as 677 things that just
	happened.
	"""
	for old, new in RENAMED_STATES.items():
		frappe.db.set_value(
			DOCTYPE, {"workflow_state": old}, "workflow_state", new, update_modified=False
		)


def verify():
	"""create_workflow and create_assignment_rule log their failures instead of raising."""
	workflow = frappe.get_doc("Workflow", WORKFLOW)

	states = {state.state: state for state in workflow.states}
	for old in RENAMED_STATES:
		if old in states:
			frappe.throw(
				f"WI-002496: {old!r} is still a state on the {WORKFLOW} workflow, so two "
				"states describe the same step."
			)

	for state, role in ((ADDRESS_BY_PRO, "PRO"), (PHOTO_BY_PRO, "PRO")):
		saved = states.get(state)
		if not saved:
			frappe.throw(f"WI-002496: the {WORKFLOW} workflow has no {state!r} state.")
		if saved.allow_edit != role:
			frappe.throw(
				f"WI-002496: {state!r} is editable by {saved.allow_edit!r}, not the {role}."
			)

	transitions = {(t.state, t.action, t.next_state) for t in workflow.transitions}
	missing = [t for t in EXPECTED_TRANSITIONS if t not in transitions]
	if missing:
		frappe.throw(
			f"WI-002496: the {WORKFLOW} workflow is missing {missing}. Check the Error Log - "
			"create_workflow swallows its failures."
		)

	for old in RENAMED_STATES:
		stranded = frappe.db.count(DOCTYPE, {"workflow_state": old})
		if stranded:
			frappe.throw(f"WI-002496: {stranded} {DOCTYPE} records still hold {old!r}.")

	field = frappe.get_meta(DOCTYPE).get_field("pro_user")
	if not field or not field.link_filters:
		frappe.throw("WI-002496: PACI.pro_user carries no link filter, so it offers every user.")
	for state in (PENDING_PRO, ADDRESS_BY_PRO, PHOTO_BY_PRO):
		if state not in (field.mandatory_depends_on or ""):
			frappe.throw(
				f"WI-002496: PACI.pro_user is not mandatory in {state!r}, so the record can "
				"reach a state only the PRO can leave with no PRO named on it."
			)

	for rule_name in RULES:
		saved = frappe.db.get_value(
			"Assignment Rule", rule_name, ["disabled", "assign_condition"], as_dict=True
		)
		if not saved:
			frappe.throw(f"WI-002496: assignment rule {rule_name!r} does not exist.")
		for old in RENAMED_STATES:
			if old in (saved.assign_condition or ""):
				frappe.throw(
					f"WI-002496: {rule_name!r} still assigns on {old!r}, a state that is gone, "
					"so it fires on nothing."
				)
