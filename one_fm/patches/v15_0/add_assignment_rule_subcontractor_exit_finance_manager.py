import frappe
from one_fm.utils import create_process_task
from one_fm.custom.assignment_rule.assignment_rule import (
	get_assignment_rule_json_file, create_assignment_rule
)

def execute():
	"""Create Process Task and Assignment Rule for Subcontractor Exit - Finance Manager."""
	task_data = {
		"process_name": "Subcontractor",
		"erp_document": "Subcontractor Exit",
		"task_description": "Assigning Finance Manager",
		"employee": "HR-EMP-00114",
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
		get_assignment_rule_json_file("subcontractor_exit_finance_manager.json"),
		process_task_name=process_task_name
	)
