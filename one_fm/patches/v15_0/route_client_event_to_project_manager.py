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

# What the analyst's site has, and all it should have.
BA_RULES = (
	"Client Event - Draft",
	"Client Event - Pending Operations Manager",
	"Client Event - Pending Project Manager",
)

# The fixtures were renamed to the analyst's names at some point, and create_assignment_rule
# writes the name it is given - so the records made under the old names were left behind,
# still enabled, and the site ends up showing five rules for three. Both of them still test
# for "Pending Approval", a state the workflow no longer has, so the Operations Manager one
# can never fire again; the Draft one still fires, duplicating "Client Event - Draft" and
# then never letting go, because the state its unassign_condition waits for never arrives.
SUPERSEDED_RULES = (
	"Returning to Operations Supervisor of Client Event",
	"Assigning Operations Manager for Approval- Client Event",
)
DRAFT_RULE = "Client Event - Draft"

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

	retire_superseded_rules()
	verify()


def retire_superseded_rules():
	"""Drop the records left behind by the fixture rename, and settle their assignments.

	Deleting a rule does not close what it assigned, and a surviving rule will not do it
	either: apply_unassign only closes the ToDos its own rule created. So an open one is
	dealt with here or never - it sits on somebody's to-do list for good.
	"""
	for rule_name in SUPERSEDED_RULES:
		if not frappe.db.exists("Assignment Rule", rule_name):
			continue

		for todo in frappe.get_all(
			"ToDo",
			filters={"assignment_rule": rule_name, "status": "Open"},
			fields=["name", "reference_name"],
		):
			state = frappe.db.get_value("Client Event", todo.reference_name, "workflow_state")
			if state == "Draft":
				# Still genuinely assigned, and "Client Event - Draft" assigns the same
				# person for the same reason. Handing it over means that rule releases it
				# when the event is submitted.
				frappe.db.set_value(
					"ToDo", todo.name, "assignment_rule", DRAFT_RULE, update_modified=False
				)
			else:
				# The event left Draft long ago; this should have been released then and
				# was not, because the state it was waiting for never existed.
				frappe.db.set_value("ToDo", todo.name, "status", "Cancelled", update_modified=False)

		frappe.delete_doc("Assignment Rule", rule_name, ignore_permissions=True, force=True)


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

	live = set(frappe.get_all("Assignment Rule", filters={"document_type": "Client Event"}, pluck="name"))
	if live != set(BA_RULES):
		frappe.throw(
			"WI-002184: Client Event should have exactly the analyst's three rules. "
			f"Extra: {sorted(live - set(BA_RULES))or 'none'}. Missing: {sorted(set(BA_RULES) - live) or 'none'}."
		)

	# close_condition is not scoped to the rule that owns the assignment: it closes every
	# ToDo on the document. With three rules on one doctype, the two that are not the
	# current state both satisfy it, so a Draft assignment was closed the moment it was
	# made. unassign_condition says the same thing and only touches its own rule's ToDos.
	using_close = frappe.get_all(
		"Assignment Rule",
		filters={"document_type": "Client Event", "close_condition": ["!=", ""]},
		pluck="name",
	)
	if using_close:
		frappe.throw(
			f"WI-002184: {using_close} use close_condition, which closes every assignment on "
			"the event rather than their own - the Draft assignment closes as soon as it opens."
		)

	stranded = frappe.db.sql(
		"""SELECT COUNT(*) FROM `tabToDo`
		   WHERE status = 'Open' AND assignment_rule IS NOT NULL
		     AND assignment_rule NOT IN (SELECT name FROM `tabAssignment Rule`)
		     AND reference_type = 'Client Event'""")[0][0]
	if stranded:
		frappe.throw(
			f"WI-002184: {stranded} open Client Event assignment(s) point at a rule that no "
			"longer exists, so nothing will ever release them."
		)

	print(f"WI-002184: Client Event routes to {NEW_STATE} when the event has a project")
