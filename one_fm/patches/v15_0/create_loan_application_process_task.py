import frappe
from one_fm.utils import create_process_if_not_exists

def execute():
    process_name = "Loan Management"
    create_process_if_not_exists(process_name)

    task_type = "Repetitive"
    if not frappe.db.exists("Task Type", task_type):
        frappe.get_doc({
            "name": task_type,
            "is_routine_task": 0,
            "doctype": "Task Type"
        }).insert(ignore_permissions=True)

    frappe.get_doc({
    "naming_series": "P-TASK-.YYYY.-",
    "process_name": "Loan Management",
    "is_erp_task": 1,
    "is_automated": 0,
    "is_active": 1,
    "erp_document": "Loan Application",
    "task": "Review and Approve Loan Application",
    "task_type": "Repetitive",
    "frequency": "Daily",
    "repeat_on_day": 0,
    "repeat_on_last_day": 0,
    "hours_per_frequency": 0.5,
    "coordination_needed": "No",
    "start_date": "2025-09-03",
    "employee": "HR-EMP-00114",
    "employee_name": "Abbas Magar Magar",
    "employee_user": "a.magar@one-fm.com",
    "department": "Operations - ONEFM",
    "report_frequency": "",
    "doctype": "Process Task",
    "coordination_method": [],
    "repeat_on_days": []
}).insert(ignore_permissions=True)