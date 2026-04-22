import frappe
from one_fm.utils import create_process_task
from one_fm.custom.assignment_rule.assignment_rule import (
	get_assignment_rule_json_file, create_assignment_rule
)

def execute():
	# Create Process Task using the helper function
	task_data = {
		"process_name": "Absence",
		"erp_document": "Absence Case",
		"task_description": "Assigning HR Officer",
		"employee": "HR-EMP-00036",
		"task_type": "Repetitive",
		"is_automated": 1,
		"method": "get_approver"
	}

	if not frappe.db.exists("Process Task", {"task": task_data["task_description"], "process_name": task_data["process_name"]}):
		create_process_task(**task_data)

	# Create Assignment Rule
	create_assignment_rule(get_assignment_rule_json_file("absence_case_hr_officer.json"))
