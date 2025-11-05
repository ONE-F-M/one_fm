import frappe
from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow
from one_fm.setup.workflow import create_workflows


def execute():
    create_workflows()
