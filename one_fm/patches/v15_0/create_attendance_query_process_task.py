import frappe

def execute():
    method = "one_fm.api.tasks.attendance_query_script"
    
    if not frappe.db.exists("Method", method):
        frappe.get_doc({
            "method": method,
            "document_type": "Attendance",
            "description": "Daily query for absent employees",
            "doctype": "Method"
        }).insert(ignore_permissions=True)

    process_name = "HR Process"
    if not frappe.db.exists("Process", process_name):
        frappe.get_doc({
            "process_name": process_name,
            "description": "HR related background checks",
            "doctype": "Process",
            "process_owner_name": "Administrator",
            "process_owner": "Administrator",
            "business_analyst": "Administrator"
        }).insert(ignore_permissions=True)

    task_type = "Routine"
    if not frappe.db.exists("Task Type", task_type):
        frappe.get_doc({
            "name": task_type,
            "is_routine_task": 1,
            "doctype": "Task Type"
        }).insert(ignore_permissions=True)

    task_desc = "Attendance Absence Check"
    if not frappe.db.exists("Process Task", {
        "process_name": process_name,
        "task": task_desc,
        "method": method,
    }):
        frappe.get_doc({
            "naming_series": "P-TASK-.YYYY.-",
            "process_name": process_name,
            "is_erp_task": 1,
            "is_automated": 1,
            "is_active": 1,
            "is_routine_task": 1,
            "erp_document": "Attendance",
            "task": task_desc,
            "task_type": task_type,
            "method": method,
            "frequency": "Cron",
            "cron_format": "30 5 * * *",
            "hours_per_frequency": 0.5,
            "coordination_needed": "No",
            "coordination_method": [],
            "repeat_on_day": 0,
            "repeat_on_days": [],
            "repeat_on_last_day": 0,
            "report_frequency": "",
            "start_date": frappe.utils.today(),
            "doctype": "Process Task"
        }).insert(ignore_permissions=True)
