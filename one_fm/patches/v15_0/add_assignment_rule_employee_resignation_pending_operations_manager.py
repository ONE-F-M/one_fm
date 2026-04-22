import frappe
from frappe.utils import today
from one_fm.custom.assignment_rule.assignment_rule import create_assignment_rule, get_assignment_rule_json_file
from one_fm.utils import create_process_task

def execute():
    process_task = create_process_task(
        process_name="Resignation",
        erp_document="Employee Resignation",
        task_description="Confirm Operational Impact of Manpower Exit",
        employee="HR-EMP-00001",
        task_type="Repetitive",
        is_routine_task=0
    )
    assignment_rule_data = get_assignment_rule_json_file("employee_resignation_pending_operations_manager.json")
    if process_task:
        process_task_name = process_task.name
        if process_task.employee:
            employee_data = frappe.db.get_value("Employee", process_task.employee, ["employee_name", "user_id", "department"], as_dict=True)
            if employee_data:
                assignment_rule_data["employee_name"] = employee_data.employee_name
                assignment_rule_data["employee_user"] = employee_data.user_id
                assignment_rule_data["department"] = employee_data.department
        create_assignment_rule(assignment_rule_data, process_task_name)
