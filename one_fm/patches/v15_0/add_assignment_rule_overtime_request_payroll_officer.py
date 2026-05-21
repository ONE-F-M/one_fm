import frappe
from one_fm.utils import create_process_task
from one_fm.custom.assignment_rule.assignment_rule import (
	get_assignment_rule_json_file, create_assignment_rule
)


def execute():
	"""Create Process Task and Assignment Rule for Overtime Request - Payroll Officer."""
	task_data = {
		"process_name": "Overtime Request",
		"erp_document": "Overtime Request",
		"task_description": "Assigning Payroll Officer",
		"employee": "HR-EMP-00022",
		"task_type": "Repetitive",
		"is_automated": 0
	}

	process_task = None
	if not frappe.db.exists("Process Task", {"task": task_data["task_description"], "process_name": task_data["process_name"]}):
		process_task = create_process_task(**task_data)

	process_task_name = None
	if process_task:
		process_task_name = process_task.name
	else:
		process_task_name = frappe.db.get_value(
			"Process Task",
			{"task": task_data["task_description"], "process_name": task_data["process_name"]},
			"name"
		)

	create_assignment_rule(
		get_assignment_rule_json_file("overtime_request_payroll_officer.json"),
		process_task_name=process_task_name
	)
