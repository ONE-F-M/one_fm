import frappe
from one_fm.utils import create_process_task
from one_fm.custom.assignment_rule.assignment_rule import (
	get_assignment_rule_json_file, create_assignment_rule
)

# Each Bonus Request assignment rule, its backing Process Task and the
# employee whose user gets the assignment (rule = "Based on Process Task").
ASSIGNMENT_RULES = [
	{
		"json_file": "bonus_request_hr_manager.json",
		"task_description": "Assigning HR Manager",
		"employee": "HR-EMP-00036",
	},
	{
		"json_file": "bonus_request_general_manager.json",
		"task_description": "Assigning General Manager",
		"employee": "HR-EMP-00001",
	},
	{
		"json_file": "bonus_request_finance_manager.json",
		"task_description": "Assigning Finance Manager",
		"employee": "HR-EMP-00114",
	},
	{
		"json_file": "bonus_request_payroll_operator.json",
		"task_description": "Assigning Payroll Officer",
		"employee": "HR-EMP-00022",
	},
]

PROCESS_NAME = "Bonus Request"
ERP_DOCUMENT = "Bonus Request"


def execute():
	"""Update Bonus Request assignment rules to the new workflow states.

	Re-applies the assign / unassign / close conditions (Payroll Operator now
	fires on "Pending Payroll Officer" instead of "Approved") and enables the
	General Manager rule. Each rule stays linked to its Process Task so the
	"Based on Process Task" selection keeps resolving the correct assignee.
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
