import frappe
from one_fm.setup.assignment_rule import create_assignment_rule, get_assignment_rule_json_file

def execute():
    
    assignment_rule_data = get_assignment_rule_json_file("subcontract_staff_attendance_operations_supervisor.json")
    create_assignment_rule(assignment_rule_data)
    
    process_tasks = frappe.get_all(
        "Process Task",
        filters={
            "process_name": "Subcontractor",
            "erp_document": "Subcontract Staff Attendance",
            "task": ["in", ["Assigning Operations Manager", "Assigning Operations Supervisor"]],
            "task_type": "Repetitive",
            "is_active": 1
        },
        fields=["name"]
    )

    for pt in process_tasks:
        frappe.db.set_value("Process Task", pt.name, "is_active", 0)
