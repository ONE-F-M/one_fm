import frappe

from one_fm.custom.assignment_rule.assignment_rule import (
	create_assignment_rule,
	get_assignment_rule_json_file,
)
from one_fm.utils import create_process_task

# Each Penalty And Investigation assignment rule, the Process Task that now names
# its assignee, and the employee that task points at (WI-001838).
ASSIGNMENT_RULES = [
	{
		"json_file": "penalty_and_investigation_hr_administrator.json",
		"task_description": "Assigning HR Administrator",
		"employee": "HR-EMP-00615",
	},
	{
		"json_file": "penalty_and_investigation_legal_manager.json",
		"task_description": "Assigning Legal Manager",
		"employee": "HR-EMP-02758",
	},
	{
		"json_file": "penalty_and_investigation_payroll_officer.json",
		"task_description": "Assigning Payroll Officer",
		"employee": "HR-EMP-00022",
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
	"""Move the Penalty And Investigation rules from "Based on Field" to "Based on Process Task".

	WI-001798 shipped these four rules assigning on `owner`, so a penalty always came
	back to whoever raised it. Each waiting state now names its assignee through a
	Process Task instead, which the process owner can reassign from the Process Task
	itself without a code change.

	The Process Task is looked up by process name and task rather than by the
	P-TASK-2026-000xx id in the supplied JSON: that series is per-site, so the ids
	only resolve on the site they were exported from. Any site missing the task gets
	it created here with the same content.
	"""
	for rule in ASSIGNMENT_RULES:
		process_task_name = frappe.db.get_value(
			"Process Task",
			{"task": rule["task_description"], "process_name": PROCESS_NAME},
			"name",
		)

		if not process_task_name:
			if not frappe.db.exists("Employee", rule["employee"]):
				# Without an employee the task has no assignee, and a rule pointing at
				# an assignee-less task silently assigns nobody. Leave the rule on its
				# current selection and let the process owner fill it in.
				frappe.log_error(
					title="WI-001838: Penalty Process Task not created",
					message=(
						f"Employee {rule['employee']} does not exist, so the Process Task "
						f"\"{rule['task_description']}\" was skipped along with "
						f"{rule['json_file']}."
					),
				)
				continue

			process_task_name = create_process_task(
				process_name=PROCESS_NAME,
				erp_document=ERP_DOCUMENT,
				task_description=rule["task_description"],
				employee=rule["employee"],
				task_type="Repetitive",
				is_automated=0,
			).name

		create_assignment_rule(
			get_assignment_rule_json_file(rule["json_file"]),
			process_task_name=process_task_name,
		)
