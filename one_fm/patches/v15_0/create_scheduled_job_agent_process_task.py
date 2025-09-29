import frappe

def execute():
    process_name = "Others"
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
            "is_routine_task": 0,
            "doctype": "Task Type"
        }).insert(ignore_permissions=True)

    method = "onefm_mcp.agents.scheduled_job_ticket_agent.run_scheduled_job_agent"
    document_type = "Scheduled Job Log"
    if not frappe.db.exists("Method", method):
        frappe.get_doc({
            "method": method,
            "document_type": document_type,
            "description": "To monitor failed scheduled jobs and create corresponding HD tickets for each one.",
            "doctype": "Method"
        }).insert(ignore_permissions=True)

    frappe.get_doc({
    "naming_series": "P-TASK-.YYYY.-",
    "process_name": "Others",
    "is_erp_task": 1,
    "is_automated": 1,
    "is_active": 1,
    "erp_document": document_type,
    "task": "Create an HD ticket for each unique failed Scheduled job.",
    "task_type": task_type,
    "method": method,
    "frequency": "Cron",
    "cron_format": "0,30 * * * *",
    "hours_per_frequency": 0.5,
    "coordination_needed": "No",
    "start_date": "2025-09-25",
    "employee": "HR-EMP-02930",
    "employee_name": "Kartik Sharma",
    "employee_user": "k.sharma@one-fm.com",
    "department": "IT - ONEFM",
    "doctype": "Process Task",
}).insert(ignore_permissions=True)