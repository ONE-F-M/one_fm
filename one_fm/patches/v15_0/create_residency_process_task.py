import frappe
from one_fm.utils import create_process_if_not_exists

def execute():
    process_name = "Residency"
    create_process_if_not_exists(process_name)

    task_type = "Repetitive"
    if not frappe.db.exists("Task Type", task_type):
        frappe.get_doc({
            "name": task_type,
            "is_routine_task": 0,
            "doctype": "Task Type"
        }).insert(ignore_permissions=True)

    task_name = "Action Preparation - Govt. Rel. Operator"
    
    if not frappe.db.exists("Process Task", {"task": task_name, "process_name": process_name}):
        frappe.get_doc({
            "naming_series": "P-TASK-.YYYY.-",
            "process_name": process_name,
            "task": task_name,
            "task_type": task_type,
            "is_erp_task": 1,
            "is_automated": 0,
            "is_active": 1,
            "is_routine_task": 0,
            "frequency": "",
            "hours_per_frequency": 0,
            "coordination_needed": "No",
            "coordination_method": [],
            "repeat_on_day": 0,
            "repeat_on_days": [],
            "repeat_on_last_day": 0,
            "report_frequency": "",
            "method": "",
            "start_date": frappe.utils.today(),
            "doctype": "Process Task"
        }).insert(ignore_permissions=True)