import frappe
from one_fm.utils import create_process_task


def execute():
	"""Create automated Process Task for Recurring Bonus Request generation."""
	task_description = "Auto-Generate Recurring Bonus Requests"
	process_name = "Bonus Request"

	if frappe.db.exists("Process Task", {
		"task": task_description,
		"process_name": process_name
	}):
		return

	create_process_task(
		process_name=process_name,
		erp_document="Bonus Request",
		task_description=task_description,
		process_description="Monthly auto-cloning of approved recurring Bonus Requests",
		task_type="Routine",
		is_routine_task=1,
		frequency="Daily",
		is_automated=1,
		method="one_fm.one_fm.doctype.bonus_request.recurring_bonus.process_recurring_bonus_requests"
	)
