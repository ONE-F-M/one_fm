"""A saved Work Permit waits in "Apply Online by GR Operator".

Draft used to save straight to "Pending by GR Operator", and Apply hung off that state.
The step where the operator applies online is now a state of its own, between Draft and
Pending GR Manager:

    Draft --Save--> Apply Online by GR Operator --Apply--> Pending GR Manager

"Pending by GR Operator" stays for the Local Transfer that comes back after payment (Paid)
and for Done -> Completed. Nothing else on the workflow changes.

The GR Operator's assignment rule has to fire at the new state too, or the operator is
handed a permit and told nothing.

## Records already in flight

Permits other than Local Transfer sitting in "Pending by GR Operator" would, under the new
flow, have only Done -> Completed, which skips the GR Manager. They move to "Apply Online by
GR Operator" and the assignment is re-run so the operator gets a ToDo. A Local Transfer
there has already been through the GR Manager and payment, so it stays.
"""

import frappe

from one_fm.custom.assignment_rule.assignment_rule import (
	create_assignment_rule,
	get_assignment_rule_json_file,
)
from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file

DOCTYPE = "Work Permit"
WORKFLOW = "Work Permit"

APPLY_ONLINE = "Apply Online by GR Operator"
PENDING_GRO = "Pending by GR Operator"

# Only a Local Transfer reaches "Pending by GR Operator" legitimately (via Paid).
IN_FLIGHT = {"workflow_state": PENDING_GRO, "work_permit_type": ["!=", "Local Transfer"]}

RULE_NAME = "Work Permit - GR Operator"
RULE_JSON = "work_permit_gr_operator.json"

EXPECTED_TRANSITIONS = (
	("Draft", "Save", APPLY_ONLINE),
	(APPLY_ONLINE, "Apply", "Pending GR Manager"),
	(PENDING_GRO, "Done", "Completed"),
	("Pending  For Payment", "Paid", PENDING_GRO),
)


def execute():
	create_workflow(get_workflow_json_file("work_permit.json"))
	create_assignment_rule(get_assignment_rule_json_file(RULE_JSON), task_for(RULE_NAME))
	moved = move_records_in_flight()
	assign(moved)
	verify()


def task_for(name):
	"""The Process Task the rule already points at, kept across the rewrite.

	The link is a site's own - the ids differ between sites - so the fixture does not carry
	one. This rule is Based on Field, so it is normally None; asked for anyway because a
	site configured by hand may not be.
	"""
	return frappe.db.get_value("Assignment Rule", name, "custom_routine_task") or None


def move_records_in_flight():
	"""Move the in-flight permits to the new state; return their names.

	update_modified=False: the move is this patch's doing, and the GRD lists sort by
	modified.
	"""
	names = frappe.get_all(DOCTYPE, filters=IN_FLIGHT, pluck="name")
	for name in names:
		frappe.db.set_value(
			DOCTYPE, name, "workflow_state", APPLY_ONLINE, update_modified=False
		)
	return names


def assign(names):
	"""Re-run the assignment rules on the moved permits so the operator gets a ToDo.

	A failure on one permit is logged and does not stop the rest.
	"""
	from frappe.automation.doctype.assignment_rule.assignment_rule import apply

	for name in names:
		try:
			doc = frappe.get_doc(DOCTYPE, name)
			apply(doc, "on_update")
		except Exception:
			frappe.log_error(
				title=f"Could not assign Work Permit {name}",
				message=frappe.get_traceback(),
			)


def verify():
	"""create_workflow and create_assignment_rule log their failures instead of raising."""
	workflow = frappe.get_doc("Workflow", WORKFLOW)

	state = next((s for s in workflow.states if s.state == APPLY_ONLINE), None)
	if not state:
		raise frappe.ValidationError(f"The {WORKFLOW} workflow has no {APPLY_ONLINE!r} state.")
	if str(state.doc_status) != "0" or state.allow_edit != "Government Relations Operator":
		raise frappe.ValidationError(
			f"{APPLY_ONLINE!r} should be doc_status 0, editable by Government Relations "
			f"Operator; it is {state.doc_status!r} / {state.allow_edit!r}."
		)

	transitions = {(t.state, t.action, t.next_state) for t in workflow.transitions}
	missing = [t for t in EXPECTED_TRANSITIONS if t not in transitions]
	if missing:
		raise frappe.ValidationError(
			f"The {WORKFLOW} workflow is missing {missing}. Check the Error Log - "
			"create_workflow swallows its failures."
		)
	stale = [
		t
		for t in (("Draft", "Save", PENDING_GRO), (PENDING_GRO, "Apply", "Pending GR Manager"))
		if t in transitions
	]
	if stale:
		raise frappe.ValidationError(f"The {WORKFLOW} workflow still has the old transitions {stale}.")

	stranded = frappe.db.count(DOCTYPE, IN_FLIGHT)
	if stranded:
		raise frappe.ValidationError(f"{stranded} {DOCTYPE} records still hold {PENDING_GRO!r}.")

	saved = frappe.db.get_value(
		"Assignment Rule",
		RULE_NAME,
		["disabled", "rule", "field", "assign_condition", "unassign_condition"],
		as_dict=True,
	)
	if not saved:
		raise frappe.ValidationError(f"Assignment rule {RULE_NAME!r} does not exist.")
	if saved.disabled or saved.rule != "Based on Field" or saved.field != "owner":
		raise frappe.ValidationError(
			f"{RULE_NAME!r} is disabled={saved.disabled} {saved.rule!r} on {saved.field!r}; "
			"it should be an enabled Based on Field rule on the owner."
		)
	for field in ("assign_condition", "unassign_condition"):
		if APPLY_ONLINE not in (saved.get(field) or ""):
			raise frappe.ValidationError(
				f"{RULE_NAME!r}.{field} does not name {APPLY_ONLINE!r}, which is where a "
				"permit now waits for its operator."
			)
