import frappe

from one_fm.custom.assignment_rule.assignment_rule import (
	create_assignment_rule,
	get_assignment_rule_json_file,
)
from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file

# WI-002184: a Client Event raised against a project is approved by that project's manager,
# not by the Operations Manager. An event with no project keeps the old route, because there
# is no project manager for it to go to.
#
# Three things have to move together or the routing half-works: the workflow needs the new
# state and the conditions that choose between the two, the doctype needs the Project Manager
# to fetch onto the event, and the assignment rule needs a field to read that manager from.
WORKFLOW_FILE = "client_event.json"

RULES = (
	"assigning_project_manager_for_approval_client_event.json",
	"assigning_operations_manager_for_approval_client_event.json",
	"returning_to_operations_supervisor_of_client_event.json",
)

NEW_STATE = "Pending Project Manager"
PM_RULE = "Client Event - Pending Project Manager"

EXPECTED_FIELDS = {
	"project_manager": "project.project_manager",
	"project_manager_user": "project_manager.user_id",
}


def execute():
	frappe.reload_doc("one_fm", "doctype", "client_event")

	ensure_workflow_state()
	create_workflow(get_workflow_json_file(WORKFLOW_FILE))

	for rule_file in RULES:
		rule = get_assignment_rule_json_file(rule_file)
		# The Process Task link is a site's own; the fixtures carry none, so an existing
		# one is passed back rather than blanked.
		create_assignment_rule(
			rule, frappe.db.get_value("Assignment Rule", rule["name"], "custom_routine_task")
		)

	verify()


def ensure_workflow_state():
	"""Workflow State.style is mandatory on this site, and a workflow cannot link to a state
	that does not exist - the save dies with LinkValidationError before create_workflow gets
	a chance to log anything useful."""
	if frappe.db.exists("Workflow State", NEW_STATE):
		return

	frappe.get_doc({
		"doctype": "Workflow State",
		"workflow_state_name": NEW_STATE,
		"style": "Warning",
	}).insert(ignore_permissions=True)


def verify():
	"""create_workflow and create_assignment_rule log their failures instead of raising."""
	meta = frappe.get_meta("Client Event")
	for fieldname, fetch_from in EXPECTED_FIELDS.items():
		field = meta.get_field(fieldname)
		if not field:
			frappe.throw(f"WI-002184: Client Event has no {fieldname!r} field.")
		if field.fetch_from != fetch_from:
			frappe.throw(
				f"WI-002184: {fieldname}.fetch_from is {field.fetch_from!r}, expected "
				f"{fetch_from!r} - the manager would never reach the event."
			)

	workflow = frappe.get_doc("Workflow", "Client Event")
	states = {state.state for state in workflow.states}
	if NEW_STATE not in states:
		frappe.throw(f"WI-002184: the Client Event workflow has no {NEW_STATE!r} state.")

	routes = {
		(t.state, t.next_state): t.condition
		for t in workflow.transitions if t.action == "Submit for Review"
	}
	if not routes.get(("Draft", NEW_STATE)):
		frappe.throw(
			f"WI-002184: Draft does not reach {NEW_STATE!r} on a condition, so every event "
			"would take whichever route the workflow lists first."
		)
	if not routes.get(("Draft", "Pending Operations Manager")):
		frappe.throw(
			"WI-002184: an event with no project has no route out of Draft."
		)

	rule = frappe.db.get_value(
		"Assignment Rule", PM_RULE, ["disabled", "rule", "field"], as_dict=True
	)
	if not rule:
		frappe.throw(f"WI-002184: assignment rule {PM_RULE!r} was not created.")
	if rule.disabled:
		frappe.throw(f"WI-002184: {PM_RULE!r} is disabled.")
	if rule.rule != "Based on Field" or rule.field != "project_manager_user":
		frappe.throw(
			f"WI-002184: {PM_RULE!r} reads {rule.field!r} rather than the project manager's "
			"user, so it would assign nobody."
		)

	print(f"WI-002184: Client Event routes to {NEW_STATE} when the event has a project")
