import frappe

def execute():
    document = "Loan"
    process_name = "Loan Management"
    if not frappe.db.exists("Process", process_name):
        frappe.get_doc({
            "process_name": process_name,
            "description": "Loan Management Process",
            "doctype": "Process",
            "process_owner_name": "Administrator",
            "process_owner": "Administrator"
        }).insert(ignore_permissions=True)

    task_type = "Repetitive"
    if not frappe.db.exists("Task Type", task_type):
        frappe.get_doc({
            "name": task_type,
            "is_routine_task": 0,
            "doctype": "Task Type"
        }).insert(ignore_permissions=True)

    task = "Action Loan Booking"
    existing_task = frappe.db.exists("Process Task", {
        "process_name": process_name,
        "task": task,
        "erp_document": document
    })
    
    if not existing_task:
        process_task = frappe.get_doc({
            "naming_series": "P-TASK-.YYYY.-",
            "process_name": process_name,
            "is_erp_task": 1,
            "is_automated": 0,
            "is_active": 1,
            "erp_document": document,
            "task": task,
            "task_type": task_type,
            "frequency": "Daily",
            "hours_per_frequency": 0.5,
            "coordination_needed": "No",
            "start_date": frappe.utils.today(),
            "repeat_on_day": 0,
            "repeat_on_days": [],
            "repeat_on_last_day": 0,
            "report_frequency": "",
            "doctype": "Process Task"
        }).insert(ignore_permissions=True)
        
        if process_task and process_task.name:
            from one_fm.custom.assignment_rule.assignment_rule import create_assignment_rule, get_assignment_rule_json_file
            assignment_rule = get_assignment_rule_json_file("action_loan_booking_senior_accountant.json")
            if assignment_rule:
                create_assignment_rule(assignment_rule, process_task.name)
    else:
        print(f"Process Task for {process_name} already exists")