from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow

def execute():
    create_workflow(get_workflow_json_file("visa_request.json"))
