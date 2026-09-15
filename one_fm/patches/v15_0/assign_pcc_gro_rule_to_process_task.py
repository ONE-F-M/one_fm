import frappe

from one_fm.custom.assignment_rule.assignment_rule import (
	create_assignment_rule,
	get_assignment_rule_json_file,
)
from one_fm.utils import create_process_task

# WI-002145: the GR Operator side of a PCC file belongs to one person, named by a Process
# Task, rather than to whoever happened to create the record - which is what the rule's
# "Based on Field" on `owner` meant. The PRO rule is left on `pro_user`: which PRO holds a
# record is a property of that record, and WI-002145 now makes the GRO choose one before the
# record can reach a PRO state at all.
RULE = "PCC Attestation-GRO"
RULE_FILE = "pcc_attestation_gro.json"

PROCESS = "Maintain Employee Legal Status"
ERP_DOCUMENT = "PCC Attestation"
TASK = "Assigning GR Operator"

# The process owner named on the work item. Resolved through the user rather than hardcoded
# as an Employee id: user_id is the same on every site, HR-EMP numbering is not.
PROCESS_OWNER_USER = "i.khot@one-fm.com"


def execute():
	frappe.reload_doc("grd", "doctype", "pcc_attestation")

	create_assignment_rule(get_assignment_rule_json_file(RULE_FILE), process_task())
	verify()


def process_task():
	"""The task that names the assignee, reused rather than duplicated on a re-run.

	create_process_task always inserts, and a second copy would leave the rule pointing at
	one of two identical tasks.
	"""
	existing = frappe.db.get_value(
		"Process Task",
		{"process_name": PROCESS, "erp_document": ERP_DOCUMENT, "task": TASK},
		"name",
	)
	if existing:
		return existing

	employee = frappe.db.get_value("Employee", {"user_id": PROCESS_OWNER_USER}, "name")
	if not employee:
		frappe.throw(
			f"WI-002145: no Employee is linked to {PROCESS_OWNER_USER}, so the Process Task "
			f"naming the {RULE} assignee cannot be created."
		)

	return create_process_task(
		process_name=PROCESS,
		erp_document=ERP_DOCUMENT,
		task_description=TASK,
		employee=employee,
	).name


def verify():
	"""create_assignment_rule logs its failures instead of raising, so check the result."""
	saved = frappe.db.get_value(
		"Assignment Rule", RULE, ["disabled", "rule", "custom_routine_task"], as_dict=True
	)
	if not saved:
		frappe.throw(f"WI-002145: assignment rule {RULE!r} was not created.")
	if saved.disabled:
		frappe.throw(f"WI-002145: assignment rule {RULE!r} is disabled.")
	if saved.rule != "Based on Process Task":
		frappe.throw(f"WI-002145: {RULE!r} is still {saved.rule!r}.")
	if not saved.custom_routine_task:
		frappe.throw(f"WI-002145: {RULE!r} has no Process Task to take its assignee from.")

	assignee = frappe.db.get_value("Process Task", saved.custom_routine_task, "employee_user")
	if not assignee:
		frappe.throw(
			f"WI-002145: the Process Task behind {RULE!r} names no employee_user, so the rule "
			"would assign nobody."
		)
