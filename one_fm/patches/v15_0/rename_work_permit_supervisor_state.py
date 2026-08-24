import frappe

from one_fm.custom.assignment_rule.assignment_rule import (
	create_assignment_rule,
	get_assignment_rule_json_file,
)
from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file

# WI-002097: the state the GRD Supervisor holds a permit in is called Pending GR Manager now.
# The name is on the workflow, on the assignment rule, in four depends_on expressions on the
# doctype - and on every permit currently sitting in it, which is the part no reload covers.
#
# The PIFSS Monthly Deduction workflows have a state of the same name belonging to a
# different process. Only Work Permit documents are moved.
OLD_STATE = "Pending By Supervisor"
NEW_STATE = "Pending GR Manager"
RULE_FILE = "work_permit_grd_supervisor.json"
RULE = "Work Permit - GRD Supervisor"


def execute():
	frappe.reload_doc("grd", "doctype", "work_permit")

	ensure_workflow_state()
	create_workflow(get_workflow_json_file("work_permit.json"))

	# The rule is "Based on Process Task", and the task is linked by WI-001827's patch rather
	# than by the export. Passed back in so re-applying the file does not blank it - a
	# task-based rule with no task assigns nobody, silently.
	create_assignment_rule(
		get_assignment_rule_json_file(RULE_FILE),
		frappe.db.get_value("Assignment Rule", RULE, "custom_routine_task"),
	)

	moved = frappe.db.count("Work Permit", {"workflow_state": OLD_STATE})
	if moved:
		frappe.db.set_value(
			"Work Permit", {"workflow_state": OLD_STATE}, "workflow_state", NEW_STATE,
			update_modified=False,
		)

	verify(moved)


def ensure_workflow_state():
	"""Create the Workflow State master the new name needs.

	create_workflow_state builds it from the workflow JSON's own `style`, and the Work Permit
	states do not carry one - so it fails on Workflow State's mandatory style and logs that
	instead of raising, and the workflow save then fails on a state that does not exist.
	Created here with the style the other waiting-on-somebody states use.
	"""
	if frappe.db.exists("Workflow State", NEW_STATE):
		return

	frappe.get_doc({
		"doctype": "Workflow State",
		"workflow_state_name": NEW_STATE,
		"style": "Warning",
	}).insert(ignore_permissions=True)


def verify(moved):
	"""create_workflow logs its failures instead of raising, so the result is checked."""
	workflow = frappe.get_doc("Workflow", "Work Permit")
	states = {state.state for state in workflow.states}

	if NEW_STATE not in states:
		frappe.throw(f"WI-002097: the Work Permit workflow has no {NEW_STATE!r} state.")
	if OLD_STATE in states:
		frappe.throw(
			f"WI-002097: the Work Permit workflow still carries {OLD_STATE!r}. Two states for "
			"the same step would split the operator's queue in half."
		)

	rule = frappe.db.get_value(
		"Assignment Rule", RULE, ["assign_condition", "rule", "custom_routine_task"], as_dict=True
	)
	if rule and NEW_STATE not in (rule.assign_condition or ""):
		frappe.throw(f"WI-002097: {RULE!r} does not assign anybody at {NEW_STATE!r}.")
	if rule and rule.rule == "Based on Process Task" and not rule.custom_routine_task:
		frappe.throw(
			f"WI-002097: {RULE!r} lost its Process Task, so it would assign nobody at "
			f"{NEW_STATE!r}."
		)

	left_behind = frappe.db.count("Work Permit", {"workflow_state": OLD_STATE})
	if left_behind:
		frappe.throw(
			f"WI-002097: {left_behind} Work Permits are still in {OLD_STATE!r}, which the "
			"workflow no longer has - they would be unreachable by any action."
		)

	print(f"WI-002097: moved {moved} Work Permits from {OLD_STATE!r} to {NEW_STATE!r}")
