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
            "is_routine_task": 1,
            "doctype": "Task Type"
        }).insert(ignore_permissions=True)

    method = "onefm_mcp.agents.agent_2_data_collection.run_agent_2"
    document_type = "Scheduled Job Log"
    if not frappe.db.exists("Method", method):
        frappe.get_doc({
            "method": method,
            "document_type": document_type,
            "description": "To scrape approved sources, match keywords and save threat feeds.",
            "doctype": "Method"
        }).insert(ignore_permissions=True)

    process_task_exists = frappe.db.exists(
        "Process Task",
        {
            "process_name": "Others",
            "method": method,
            "employee": "HR-EMP-02930"
        }
    )

    if not process_task_exists:
        frappe.get_doc({
        "naming_series": "P-TASK-.YYYY.-",
        "process_name": "Others",
        "is_erp_task": 1,
        "is_automated": 1,
        "is_active": 1,
        "erp_document": document_type,
        "task": "Scrape and Save Threat Feeds - Agent 2",
        "task_type": task_type,
        "method": method,
        "frequency": "Cron",
        "cron_format": "0 8,20 * * *",
        "hours_per_frequency": 0.5,
        "coordination_needed": "No",
        "start_date": "2025-10-25",
        "employee": "HR-EMP-02930",
        "employee_name": "Kartik Sharma",
        "employee_user": "k.sharma@one-fm.com",
        "department": "IT - ONEFM",
        "doctype": "Process Task",
    }).insert(ignore_permissions=True)