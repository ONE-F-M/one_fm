import frappe
from one_fm.utils import create_process_task
from one_fm.custom.assignment_rule.assignment_rule import (
	get_assignment_rule_json_file, create_assignment_rule
)

def execute():
	"""Create Process Task and Assignment Rule for Leave Application - Approved (GS Employee)."""
	task_data = {
		"process_name": "Annual Leave",
		"erp_document": "Leave Application",
		"task_description": "Assigning GS Employee",
		"employee": "HR-EMP-03218",
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
		get_assignment_rule_json_file("leave_application_approved_gs_employee.json"),
		process_task_name=process_task_name
	)
