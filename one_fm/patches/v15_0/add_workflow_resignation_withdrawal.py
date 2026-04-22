from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow


def execute():
    workflow_json = get_workflow_json_file("employee_resignation_withdrawal.json")
    create_workflow(workflow_json)

    