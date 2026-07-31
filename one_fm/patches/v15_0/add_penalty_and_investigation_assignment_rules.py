import frappe
from one_fm.utils import create_process_task
from one_fm.custom.assignment_rule.assignment_rule import (
	get_assignment_rule_json_file, create_assignment_rule
)

# Each Penalty And Investigation workflow tier, its backing Process Task and the
# employee whose user gets the assignment (rule = "Based on Process Task").
ASSIGNMENT_RULES = [
	{
		"json_file": "penalty_and_investigation_hr_administrator.json",
		"task_description": "Assigning HR Administrator",
		"employee": "HR-EMP-02717",
	},
	{
		"json_file": "penalty_and_investigation_legal_manager.json",
		"task_description": "Assigning Legal Manager",
		"employee": "HR-EMP-02125",
	},
	{
		"json_file": "penalty_and_investigation_general_manager.json",
		"task_description": "Assigning General Manager",
		"employee": "HR-EMP-00001",
	},
]

PROCESS_NAME = "Penalty"
ERP_DOCUMENT = "Penalty And Investigation"


def execute():
	"""Assign a penalty to whoever owes it an action (WI-001798).

	One rule per waiting state of the workflow added in WI-001796, each linked to a
	Process Task so "Based on Process Task" resolves the tier's current holder
	without hardcoding a user on the rule itself.
	"""
	for rule in ASSIGNMENT_RULES:
		process_task_name = frappe.db.get_value(
			"Process Task",
			{"task": rule["task_description"], "process_name": PROCESS_NAME},
			"name",
		)

		if not process_task_name:
			process_task = create_process_task(
				process_name=PROCESS_NAME,
				erp_document=ERP_DOCUMENT,
				task_description=rule["task_description"],
				employee=rule["employee"],
				task_type="Repetitive",
				is_automated=0,
			)
			process_task_name = process_task.name

		create_assignment_rule(
			get_assignment_rule_json_file(rule["json_file"]),
			process_task_name=process_task_name,
		)

	# create_assignment_rule logs its failures instead of raising, and a rule saved
	# without its Process Task assigns nobody at all - so verify rather than trust.
	for rule in ASSIGNMENT_RULES:
		name = get_assignment_rule_json_file(rule["json_file"])["name"]
		task = frappe.db.get_value("Assignment Rule", name, "custom_routine_task")
		if not task:
			frappe.log_error(
				title="Penalty Assignment Rule Not Applied",
				message=f"Assignment Rule '{name}' is missing or has no Process Task linked.",
			)
