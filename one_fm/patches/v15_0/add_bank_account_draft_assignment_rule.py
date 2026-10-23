import frappe

from one_fm.setup.assignment_rule import create_assignment_rule, get_assignment_rule_json_file
from one_fm.utils import create_process_task

# Assigns Draft Bank Accounts to the HR onboarding administrator through a Process Task.
#
# Two corrections to the BA export:
#  - it tested `doc.workflow_state`. Conditions are evaluated with the document dict as
#    locals, so `doc` is undefined and the rule never fired.
#  - its `!= "Draft"` check was a close_condition. Both close_condition and
#    unassign_condition cancel or close every ToDo on the document, which would shut the
#    Payroll Officer ToDo added on Open Request. Both are empty; the rule's own ToDo is
#    cancelled by one_fm.utils.close_bank_account_draft_todos.
RULE_NAME = "Action Draft - HR User"
RULE_JSON = "action_draft_hr_user.json"
PROCESS = "Others"
DOCTYPE = "Bank Account"
TASK = "Assigning Bank Account Creation Task"
EMPLOYEE = "HR-EMP-03404"


def execute():
	create_assignment_rule(get_assignment_rule_json_file(RULE_JSON), process_task())
	verify()


def process_task():
	"""Reuse the task on a re-run; create_process_task always inserts."""
	existing = frappe.db.get_value(
		"Process Task",
		{"process_name": PROCESS, "erp_document": DOCTYPE, "task": TASK, "employee": EMPLOYEE},
		"name",
	)
	if existing:
		return existing

	return create_process_task(
		process_name=PROCESS,
		erp_document=DOCTYPE,
		task_description=TASK,
		employee=EMPLOYEE,
	).name


def verify():
	"""create_assignment_rule logs failures instead of raising."""
	saved = frappe.db.get_value(
		"Assignment Rule", RULE_NAME, ["disabled", "custom_routine_task"], as_dict=True
	)
	if not saved:
		frappe.throw(f"Assignment rule {RULE_NAME!r} was not created.")
	if saved.disabled:
		frappe.throw(f"Assignment rule {RULE_NAME!r} is disabled.")
	if not saved.custom_routine_task:
		frappe.throw(f"Assignment rule {RULE_NAME!r} has no Process Task.")
