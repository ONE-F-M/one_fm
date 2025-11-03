import frappe
from frappe.utils import today
from one_fm.setup.assignment_rule import create_assignment_rule, get_assignment_rule_json_file
from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow

def execute():
    create_process_task()

def create_process_task():
    process_name = "Attendance Process"
    if not frappe.db.exists("Process", process_name):
        frappe.get_doc({
            "process_name": process_name,
            "description": process_name,
            "doctype": "Process",
            "process_owner_name": "Administrator",
            "process_owner": "Administrator"
        }).insert(ignore_permissions=True)

    task_type = "Routine"
    if not frappe.db.exists("Task Type", task_type):
        frappe.get_doc({
            "name": task_type,
            "is_routine_task": 1,
            "doctype": "Task Type"
        }).insert(ignore_permissions=True)

    method = "one_fm.one_fm.doctype.leave_handover.leave_handover.reliever_assignment_on_leave_start"
    document_type = "Leave Handover"
    if not frappe.db.exists("Method", method):
        frappe.get_doc({
            "method": method,
            "document_type": document_type,
            "description": "To assign reliever on leave start date from leave handover.",
            "doctype": "Method"
        }).insert(ignore_permissions=True)

    process_task = frappe.get_doc({
        "naming_series": "P-TASK-.YYYY.-",
        "process_name": process_name,
        "is_erp_task": 1,
        "is_automated": 1,
        "is_active": 1,
        "erp_document": document_type,
        "task": "Assign reliever on leave start date from leave handover.",
        "task_type": task_type,
        "method": method,
        "frequency": "Cron",
        "cron_format": "45 23 * * *",
        "hours_per_frequency": 0.5,
        "coordination_needed": "No",
        "start_date": today(),
        "doctype": "Process Task",
    }).insert(ignore_permissions=True)
    return process_task.name