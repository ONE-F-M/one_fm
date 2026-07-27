import frappe
from one_fm.custom.workflow.workflow import get_workflow_json_file, create_workflow

def execute():
	print("=== Patch: Registering T4 Admin role and reloading custom workflows ===")
	
	# 1. Ensure T4 Admin role exists in DB
	if not frappe.db.exists("Role", "T4 Admin"):
		print("Creating 'T4 Admin' role")
		frappe.get_doc({
			"doctype": "Role",
			"role_name": "T4 Admin"
		}).insert(ignore_permissions=True)

	# 2. Reload Doctypes to apply updated T4 Admin permissions from JSON files
	print("Reloading PMR and Resignation doctypes...")
	frappe.reload_doc("one_fm", "doctype", "project_manpower_request", force=True)
	frappe.reload_doc("one_fm", "doctype", "employee_resignation", force=True)

	# 3. Reload/update workflows
	print("Reloading PMR and Employee Resignation workflows...")
	
	pmr_wf = get_workflow_json_file("project_manpower_request.json")
	create_workflow(pmr_wf)
	
	res_wf = get_workflow_json_file("employee_resignation.json")
	create_workflow(res_wf)
	
	frappe.clear_cache(doctype="Project Manpower Request")
	frappe.clear_cache(doctype="Employee Resignation")
	print("Workflows reloaded successfully.")
