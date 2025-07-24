import frappe

def execute():
    if not frappe.db.exists("Method", "one_fm.one_fm.doctype.attendance_check.attendance_check.schedule_attendance_check"):
        frappe.get_doc({
            "method":"one_fm.one_fm.doctype.attendance_check.attendance_check.schedule_attendance_check",
            "document_type":"Attendance Check",
            "description":"Attendance Check",
            "doctype":"Method"
        }).insert(ignore_permissions=True)

    if not frappe.db.exists("Process", "Attendance Check"):
        frappe.get_doc({
            "process_name":"Attendance Check",
            "description":"Attendance Check",
            "doctype":"Process",
            "process_owner_name":"Administrator",
            "process_owner":"Administrator"
        }).insert(ignore_permissions=True)

    if not frappe.db.exists("Task Type", "Routine"):
        frappe.get_doc({
            "name":"Routine",
            "is_routine_task":1,
            "doctype":"Task Type"
        }).insert(ignore_permissions=True)

    frappe.get_doc({
        "naming_series":"P-TASK-.YYYY.-",
        "process_name":"Attendance Check",
        "is_erp_task":1,
        "is_automated":1,
        "is_active":1,
        "erp_document":"Attendance Check",
        "task":"Attendance Check",
        "task_type":"Routine",
        "is_routine_task":1,
        "method":"one_fm.one_fm.doctype.attendance_check.attendance_check.schedule_attendance_check",
        "frequency":"Cron",
        "cron_format":"15 13 * * *",
        "hours_per_frequency":0.5,
        "coordination_needed":"No",
        "start_date":"2025-07-21",
        "doctype":"Process Task"
    }).insert(ignore_permissions=True)
