import frappe
from frappe.utils import today
from one_fm.setup.assignment_rule import create_assignment_rule, get_assignment_rule_json_file
from one_fm.utils import create_process_task

def execute():
    process_task = create_process_task(
        "Annual Leave",
        "Leave Acknowledgement Form",
        "Action Leave Acknowledgement Form - HR Operator",
        employee="HR-EMP-02717",
        process_owner=None,
        business_analyst=None,
        task_type="Repetitive",
        is_routine_task=0
    )
    
    assignment_rule_data = get_assignment_rule_json_file("leave_acknowledgement_form_pending_hr.json")
    
    process_task_name = None
    if process_task:
        process_task_name = process_task.name
        # Add process task name to assignment rule data dynamically
        assignment_rule_data["custom_routine_task"] = process_task_name        
    create_assignment_rule(assignment_rule_data, process_task_name)
