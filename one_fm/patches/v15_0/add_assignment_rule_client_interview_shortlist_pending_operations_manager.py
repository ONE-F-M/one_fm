import frappe
from one_fm.setup.assignment_rule import create_assignment_rule, get_assignment_rule_json_file
from one_fm.utils import create_process_task


def execute():
	"""Story 4: Create 'Client Interview Shortlist - Pending Operations Manager' assignment rule.
	Assigns the Operations Manager via Process Task when the record is Pending Operations Manager.
	Rule type: Based on Process Task.

	Follows the same pattern as add_assignment_rule_rfm_warehouse_supervisor.py."""

	# Create the Process Task (idempotent — returns existing if already present)
	process_task = create_process_task(
		process_name="Client Interview",
		erp_document="Client Interview Shortlist",
		task_description="Review and Approve Client Interview Shortlist",
		employee="HR-EMP-00001",
		process_owner=None,
		business_analyst=None,
		task_type="Repetitive",
		is_routine_task=0,
		is_automated=0,
		method="",
	)

	# Load assignment rule JSON (rule: Based on Process Task)
	assignment_rule_data = get_assignment_rule_json_file(
		"client_interview_shortlist_pending_operations_manager.json"
	)

	# Enrich with employee details from the Process Task
	process_task_name = None
	if process_task:
		process_task_name = process_task.name
		if process_task.employee:
			employee_data = frappe.db.get_value(
				"Employee",
				process_task.employee,
				["employee_name", "user_id", "department"],
				as_dict=True,
			)
			if employee_data:
				assignment_rule_data["employee_name"] = employee_data.employee_name
				assignment_rule_data["employee_user"] = employee_data.user_id
				assignment_rule_data["department"] = employee_data.department

	# Create/update Assignment Rule linked to Process Task
	create_assignment_rule(assignment_rule_data, process_task_name)
