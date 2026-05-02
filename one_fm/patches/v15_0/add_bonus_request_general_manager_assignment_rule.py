import frappe
from one_fm.utils import create_process_task
from one_fm.custom.assignment_rule.assignment_rule import (
	get_assignment_rule_json_file, create_assignment_rule
)

def execute():
	"""Create Process Task and Assignment Rule for Bonus Request - General Manager."""
	task_data = {
		"process_name": "Bonus Request",
		"erp_document": "Bonus Request",
		"task_description": "Assigning General Manager",
		"employee": "HR-EMP-00001",
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
		get_assignment_rule_json_file("bonus_request_general_manager.json"),
		process_task_name=process_task_name
	)
