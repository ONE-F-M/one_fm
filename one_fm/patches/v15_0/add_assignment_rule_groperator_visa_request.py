import frappe
from one_fm.custom.assignment_rule.assignment_rule import (
    get_assignment_rule_json_file, create_assignment_rule
)
from one_fm.utils import create_process_task


def execute():
    # Create the process task and link it to the assignment rule
    process_task = create_process_task(
        process_name="Visa",
        erp_document="Visa Request",
        task_description="Assign Government Relations Operator",
        employee="HR-EMP-00775",
        task_type="Repetitive",
        is_routine_task=0
    )

    create_assignment_rule(
        get_assignment_rule_json_file("groperator_visa_request.json"),
        process_task.name
    )
