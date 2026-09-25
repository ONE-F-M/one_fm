"""WI-002494: the Medical Insurance workflow and its assignment rule, as the BA site holds them.

Three things change together, and none of them works without the others:

  - the state a submitted application waits in is "Apply Online by GR Operator", not
    "Apply Online by PRO". No PRO touches Medical Insurance - the GR Operator applies
    online themselves - and the old name sent operators looking for a handover that does
    not exist;
  - every state now writes `status`, so the Data field beside the workflow says the same
    thing the workflow does instead of whatever it was left at;
  - "Medical Insurance - GRO" is new. Medical Insurance had no assignment rule at all, so
    an application sat in Draft on nobody's desk until its owner remembered it.

The 502 applications already waiting in the old state are renamed here. Leaving them
behind would strand every one of them: the renamed state has the only transition out, so
a row still holding "Apply Online by PRO" would have no action at all.
"""

import frappe

from one_fm.custom.assignment_rule.assignment_rule import (
	create_assignment_rule,
	get_assignment_rule_json_file,
)
from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file

DOCTYPE = "Medical Insurance"
OLD_STATE = "Apply Online by PRO"
NEW_STATE = "Apply Online by GR Operator"
RULE_NAME = "Medical Insurance - GRO"
RULE_JSON = "medical_insurance_gro.json"

# What each state writes into `status`. Checked after the fact because create_workflow
# logs its failures to the Error Log instead of raising - it can report success having
# changed nothing.
EXPECTED_STATUS = {
	"Draft": "Draft",
	NEW_STATE: "Draft",
	"Completed": "Submitted",
	"Cancelled": "Canceled",
}

EXPECTED_TRANSITIONS = (
	("Draft", "Submit", NEW_STATE),
	(NEW_STATE, "Done", "Completed"),
)


def execute():
	create_workflow(get_workflow_json_file("medical_insurance.json"))
	rename_existing_documents()
	create_assignment_rule(get_assignment_rule_json_file(RULE_JSON))
	verify()


def rename_existing_documents():
	"""Move the applications waiting in the old state onto the new one.

	update_modified=False: the rename is this patch's doing, not an operator's, and the
	GRD lists are sorted by modified - 502 applications jumping to the top of them would
	read as 502 things that just happened.
	"""
	frappe.db.set_value(
		DOCTYPE, {"workflow_state": OLD_STATE}, "workflow_state", NEW_STATE, update_modified=False
	)


def verify():
	workflow = frappe.get_doc("Workflow", DOCTYPE)

	states = {state.state: state for state in workflow.states}
	for state, status in EXPECTED_STATUS.items():
		saved = states.get(state)
		if not saved:
			frappe.throw(f"WI-002494: the {DOCTYPE} workflow has no {state!r} state.")
		if saved.update_field != "status" or saved.update_value != status:
			frappe.throw(
				f"WI-002494: {state!r} writes {saved.update_field}={saved.update_value!r}, "
				f"expected status={status!r}."
			)

	if OLD_STATE in states:
		frappe.throw(
			f"WI-002494: {OLD_STATE!r} is still a state on the {DOCTYPE} workflow, so two "
			"states describe the same step."
		)

	transitions = {(t.state, t.action, t.next_state) for t in workflow.transitions}
	missing = [t for t in EXPECTED_TRANSITIONS if t not in transitions]
	if missing:
		frappe.throw(
			f"WI-002494: the {DOCTYPE} workflow is missing {missing}. Check the Error Log - "
			"create_workflow swallows its failures."
		)

	stranded = frappe.db.count(DOCTYPE, {"workflow_state": OLD_STATE})
	if stranded:
		frappe.throw(
			f"WI-002494: {stranded} {DOCTYPE} records still hold {OLD_STATE!r}, which has no "
			"transition out of it."
		)

	if not frappe.db.exists("Assignment Rule", RULE_NAME):
		frappe.throw(
			f"WI-002494: {RULE_NAME!r} was not created - create_assignment_rule also logs "
			"its failures instead of raising, so check the Error Log."
		)
