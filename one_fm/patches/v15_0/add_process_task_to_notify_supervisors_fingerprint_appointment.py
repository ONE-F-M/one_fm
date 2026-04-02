import frappe
from one_fm.utils import create_process_if_not_exists

def execute():
    method = "one_fm.grd.doctype.fingerprint_appointment.fingerprint_appointment.notify_supervisor_of_pending_fingerprint_appointment"
    document = "Fingerprint Appointment"
    
    if not frappe.db.exists("Method", method):
        frappe.get_doc({
            "method": method,
            "document_type": document,
            "description": "Notify Supervisor of Pending Fingerprint Appointment",
            "doctype": "Method"
        }).insert(ignore_permissions=True)

    process_name = "Residency"
    create_process_if_not_exists(process_name)

    task_type = "Routine"
    if not frappe.db.exists("Task Type", task_type):
        frappe.get_doc({
            "name": task_type,
            "is_routine_task": 1,
            "doctype": "Task Type"
        }).insert(ignore_permissions=True)

    task_name = "Fingerprint Appointment Supervisor Notification"
    if not frappe.db.exists("Process Task", {"task": task_name}):
        frappe.get_doc({
            "naming_series": "P-TASK-.YYYY.-",
            "process_name": process_name,
            "is_erp_task": 1,
            "is_automated": 1,
            "is_active": 1,
            "erp_document": document,
            "task": task_name,
            "task_type": task_type,
            "method": method,
            "frequency": "Cron",
            "cron_format": "0 8 * * *",
            "hours_per_frequency": 0.500,
            "coordination_needed": "No",
            "start_date": frappe.utils.today(),
            "doctype": "Process Task"
        }).insert(ignore_permissions=True)