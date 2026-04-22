import frappe
from one_fm.utils import create_process_task
from one_fm.custom.assignment_rule.assignment_rule import (
	get_assignment_rule_json_file, create_assignment_rule
)

def execute():
	# Create Process Tasks using the helper function
	tasks_to_create = [
		{
			"process_name": "Absence",
			"erp_document": "Formal Hearing",
			"task_description": "Assigning Operations Manager",
			"employee": "HR-EMP-00250",
			"task_type": "Repetitive",
			"is_automated": 0
		},
		{
			"process_name": "Absence",
			"erp_document": "Formal Hearing",
			"task_description": "Assigning HR Manager",
			"employee": "HR-EMP-00036",
			"task_type": "Repetitive",
			"is_automated": 0
		},
		{
			"process_name": "Absence",
			"erp_document": "Formal Hearing",
			"task_description": "Assigning General Manager",
			"employee": "HR-EMP-00001",
			"task_type": "Repetitive",
			"is_automated": 0
		}
	]

	for task in tasks_to_create:
		if not frappe.db.exists("Process Task", {"task": task["task_description"], "process_name": task["process_name"]}):
			create_process_task(**task)

	# Create Assignment Rules
	assignment_rules = [
		"formal_hearing_operations_manager.json",
		"formal_hearing_hr_manager.json",
		"formal_hearing_general_manager.json"
	]

	for rule_file in assignment_rules:
		create_assignment_rule(get_assignment_rule_json_file(rule_file))
