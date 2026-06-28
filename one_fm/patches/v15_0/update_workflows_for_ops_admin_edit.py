import frappe
from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow

def execute():
	print("=== Patch: Updating PMR and Resignation workflows for Operation Admin edit ===")
	# Reload Project Manpower Request workflow
	pmr_wf = get_workflow_json_file("project_manpower_request.json")
	create_workflow(pmr_wf)
	
	# Reload Employee Resignation workflow
	res_wf = get_workflow_json_file("employee_resignation.json")
	create_workflow(res_wf)
	
	frappe.clear_cache(doctype="Project Manpower Request")
	frappe.clear_cache(doctype="Employee Resignation")
	print("Workflows reloaded successfully.")
