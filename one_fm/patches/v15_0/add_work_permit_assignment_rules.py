import frappe

from one_fm.setup.assignment_rule import create_assignment_rule, get_assignment_rule_json_file
from one_fm.utils import create_process_task

# WI-001827: the three Work Permit assignment rules the work item links to, applied as
# exported. Each is "Based on Process Task", so the assignee comes from the task's
# employee rather than a user list on the rule.
#
# Two things in the export do not work as written; both are left as given for the BA to
# decide on, and both are pinned by tests so the state of them is visible:
#  - the GRD Supervisor rule tests `doc.workflow_state`. assign_condition is evaluated
#    with the document's own dict as locals, so `doc` is not a name that exists: the rule
#    never fires and every save msgprints "Auto assignment failed: name 'doc' is not
#    defined".
#  - it names the payment state "Pending For Payment"; the state is "Pending  For Payment"
#    with two spaces, so nothing matches it and the supervisor is never assigned while a
#    transfer waits for payment.
PROCESS = "Residency"
RULES = [
	{
		"json": "work_permit_pro.json",
		"name": "Work Permit-PRO",
		"task": "Assigning PRO in Work Permit",
		"employee": "HR-EMP-00114",
	},
	{
		"json": "work_permit_grd_supervisor.json",
		"name": "Work Permit - GRD Supervisor",
		"task": "Assigning GRD Supervisor in W",
		"employee": "HR-EMP-00775",
	},
	{
		"json": "work_permit_gr_operator.json",
		"name": "Work Permit - GR Operator",
		"task": "Set new Work Permit Expiry Date and mark as completed.",
		"employee": "HR-EMP-00114",
	},
]


def execute():
	for rule in RULES:
		task = process_task_for(rule)
		create_assignment_rule(get_assignment_rule_json_file(rule["json"]), task)

	verify()


def process_task_for(rule):
	"""The task that names the assignee, reused rather than duplicated on a re-run.

	create_process_task always inserts, and a second copy would leave the rule pointing
	at one of two identical tasks.
	"""
	existing = frappe.db.get_value(
		"Process Task",
		{
			"process_name": PROCESS,
			"erp_document": "Work Permit",
			"task": rule["task"],
			"employee": rule["employee"],
		},
		"name",
	)
	if existing:
		return existing

	return create_process_task(
		process_name=PROCESS,
		erp_document="Work Permit",
		task_description=rule["task"],
		employee=rule["employee"],
	).name


def verify():
	"""create_assignment_rule logs failures instead of raising, so check the result."""
	for rule in RULES:
		saved = frappe.db.get_value(
			"Assignment Rule", rule["name"], ["disabled", "custom_routine_task"], as_dict=True
		)
		if not saved:
			frappe.throw(f"WI-001827: assignment rule {rule['name']!r} was not created.")
		if saved.disabled:
			frappe.throw(f"WI-001827: assignment rule {rule['name']!r} is disabled.")
		if not saved.custom_routine_task:
			frappe.throw(f"WI-001827: {rule['name']!r} has no Process Task to take its assignee from.")
