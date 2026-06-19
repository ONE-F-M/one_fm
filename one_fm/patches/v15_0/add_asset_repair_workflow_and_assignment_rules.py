import frappe
from one_fm.utils import create_process_task
from one_fm.custom.assignment_rule.assignment_rule import (
	get_assignment_rule_json_file, create_assignment_rule
)
from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow


def execute():
	"""Create Workflow, Process Tasks, and Assignment Rules for Asset Repair."""
	# 1. Create the Asset Repair workflow
	create_workflow(get_workflow_json_file("asset_repair.json"))

	# 2. Create Process Task & Assignment Rule for GS Admin
	_create_gs_admin_assignment_rule()

	# 3. Create Process Task & Assignment Rule for Warehouse Supervisor
	_create_warehouse_supervisor_assignment_rule()


def _create_gs_admin_assignment_rule():
	"""Create Process Task and Assignment Rule for Asset Repair - GS Admin."""
	task_data = {
		"process_name": "Asset Maintenance",
		"erp_document": "Asset Repair",
		"task_description": "Assigning Asset Maintenance Request by GS Admin",
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
		get_assignment_rule_json_file("assign_to_gs_admin_asset_repair.json"),
		process_task_name=process_task_name
	)


def _create_warehouse_supervisor_assignment_rule():
	"""Create Process Task and Assignment Rule for Asset Repair - Warehouse Supervisor."""
	task_data = {
		"process_name": "Asset Maintenance",
		"erp_document": "Asset Repair",
		"task_description": "Assigning Warehouse Supervisor to Asset Maintenance Request",
		"employee": "HR-EMP-02117",
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
		get_assignment_rule_json_file("assign_warehouse_supervisor_asset_repair.json"),
		process_task_name=process_task_name
	)
