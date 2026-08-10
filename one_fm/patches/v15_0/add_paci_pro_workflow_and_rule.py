import frappe

from one_fm.custom.assignment_rule.assignment_rule import (
	create_assignment_rule,
	get_assignment_rule_json_file,
)
from one_fm.custom.workflow.workflow import create_workflow, get_workflow_json_file
from one_fm.utils import create_process_task

# WI-001830: the PRO tier the BA site added to the PACI workflow, and the rule that puts
# a Pending PRO record on the PRO's desk.
WORKFLOW = "PACI"
RULE_NAME = "PACI-PRO"
RULE_JSON = "paci_pro.json"

# The states and transitions this patch is responsible for. Verified after the fact
# because create_workflow logs its failures to the Error Log instead of raising, so it
# can report success having changed nothing.
EXPECTED_STATES = ("Pending PRO", "Pending by PACI", "Rejected")
EXPECTED_TRANSITIONS = (
	("Draft", "Save", "Pending PRO"),
	("Pending PRO", "Submit", "Pending by PACI"),
	("Pending by PACI", "Approve", "Completed"),
	("Pending by PACI", "Reject", "Rejected"),
)

# allow_edit holds one role per state row, so granting two roles on Completed means two
# rows for it - which is how the BA site does it, and what
# frappe.workflow.get_document_state_roles reads. Verified here because treating the
# second row as a duplicate is exactly what took the operator's edit rights away.
COMPLETED_EDIT_ROLES = ("System Manager", "Government Relations Operator")

# The rule selects its assignee from this Process Task, so the task has to exist before
# the rule does - a rule pointing at a missing task silently assigns nobody.
PROCESS_NAME = "Maintain Employee Legal Status"
TASK_DESCRIPTION = "Action PACI - Apply in PACI"
TASK_EMPLOYEE = "HR-EMP-00775"


def execute():
	"""Add the PACI PRO tier and its assignment rule (WI-001830)."""
	create_workflow(get_workflow_json_file("paci.json"))
	verify_workflow()
	apply_assignment_rule()


def verify_workflow():
	workflow = frappe.get_doc("Workflow", WORKFLOW)

	states = {state.state for state in workflow.states}
	missing_states = [state for state in EXPECTED_STATES if state not in states]

	transitions = {(t.state, t.action, t.next_state) for t in workflow.transitions}
	missing_transitions = [t for t in EXPECTED_TRANSITIONS if t not in transitions]

	completed_roles = {state.allow_edit for state in workflow.states if state.state == "Completed"}
	missing_roles = [role for role in COMPLETED_EDIT_ROLES if role not in completed_roles]

	if missing_states or missing_transitions or missing_roles:
		frappe.throw(
			f"WI-001830: the {WORKFLOW} workflow was not updated. "
			f"Missing states: {missing_states or 'none'}. "
			f"Missing transitions: {missing_transitions or 'none'}. "
			f"Roles that cannot edit Completed: {missing_roles or 'none'}. "
			"Check the Error Log - create_workflow swallows its failures."
		)


def apply_assignment_rule():
	process_task_name = frappe.db.get_value(
		"Process Task", {"task": TASK_DESCRIPTION, "process_name": PROCESS_NAME}, "name"
	)

	if not process_task_name:
		if not frappe.db.exists("Employee", TASK_EMPLOYEE):
			# Leave the rule alone rather than create one that assigns nobody, and say why.
			frappe.log_error(
				title="WI-001830: PACI Process Task not created",
				message=(
					f"Employee {TASK_EMPLOYEE} does not exist, so the Process Task "
					f'"{TASK_DESCRIPTION}" was skipped along with {RULE_JSON}.'
				),
			)
			return

		process_task_name = create_process_task(
			process_name=PROCESS_NAME,
			erp_document="PACI",
			task_description=TASK_DESCRIPTION,
			employee=TASK_EMPLOYEE,
			task_type="Repetitive",
			is_routine_task=0,
		).name

	# Who covers the tier is the process owner's call, so an existing task's assignee is
	# left exactly as the site has it.
	create_assignment_rule(get_assignment_rule_json_file(RULE_JSON), process_task_name=process_task_name)

	if not frappe.db.exists("Assignment Rule", RULE_NAME):
		frappe.throw(
			f"WI-001830: {RULE_NAME} was not created - create_assignment_rule also logs "
			"its failures instead of raising, so check the Error Log."
		)
