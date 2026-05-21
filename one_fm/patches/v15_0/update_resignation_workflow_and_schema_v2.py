import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
	# 1. Sync Employee Resignation schema to ensure shift_working field exists in DB
	frappe.reload_doc("one_fm", "doctype", "employee_resignation", force=True)
	frappe.clear_cache(doctype="Employee Resignation")
	frappe.db.updatedb("Employee Resignation")





	# 2. Backfill shift_working field for all existing Employee Resignation documents
	resignations = frappe.get_all("Employee Resignation", fields=["name"])
	for r in resignations:
		doc = frappe.get_doc("Employee Resignation", r.name)
		if doc.employees and doc.employees[0].employee:
			shift_working = frappe.db.get_value("Employee", doc.employees[0].employee, "shift_working") or 0
			frappe.db.set_value("Employee Resignation", doc.name, "shift_working", shift_working, update_modified=False)

	# 3. Rebuild Workflow with simplified shift_working condition
	workflow_name = "Employee Resignation"
	if frappe.db.exists("Workflow", workflow_name):
		wf = frappe.get_doc("Workflow", workflow_name)
		# Rebuild states
		wf.set("states", [])
		wf.set("transitions", [])
		
		states_data = [
			{"state": "Draft", "doc_status": 0, "update_field": "status", "update_value": "Pending", "allow_edit": "Employee", "style": "Primary"},
			{"state": "Pending Supervisor", "doc_status": 0, "update_field": "status", "update_value": "Pending", "allow_edit": "Employee", "style": "Warning"},
			{"state": "Pending Relieving Date Correction", "doc_status": 0, "update_field": "status", "update_value": "Pending", "allow_edit": "Employee", "style": "Danger"},
			{"state": "Pending Operations Manager", "doc_status": 0, "update_field": "status", "update_value": "Pending", "allow_edit": "Operations Manager", "style": "Warning"},
			{"state": "Approved", "doc_status": 1, "update_field": "status", "update_value": "Approved", "allow_edit": "Offboarding Officer", "style": "Success"},
			{"state": "Withdrawn", "doc_status": 1, "update_field": "status", "update_value": "Withdrawn", "allow_edit": "System Manager", "style": "Inverse"}
		]
		for s in states_data:
			wf.append("states", s)
			
		transitions_data = [
			{"state": "Draft", "action": "Submit for Review", "next_state": "Pending Supervisor", "allowed": "Employee"},
			{"state": "Pending Supervisor", "action": "Submit for Approval", "next_state": "Pending Operations Manager", "allowed": "Employee", "allowed_user_field": "supervisor", "condition": "doc.shift_working == 1"},
			{"state": "Pending Supervisor", "action": "Approve", "next_state": "Approved", "allowed": "Employee", "allowed_user_field": "supervisor", "condition": "doc.shift_working == 0"},
			{"state": "Pending Supervisor", "action": "Request Relieving Date Change", "next_state": "Pending Relieving Date Correction", "allowed": "Employee", "allowed_user_field": "supervisor"},
			{"state": "Pending Relieving Date Correction", "action": "Resubmit Date", "next_state": "Pending Supervisor", "allowed": "Employee"},
			{"state": "Pending Operations Manager", "action": "Approve", "next_state": "Approved", "allowed": "Operations Manager"}
		]
		for t in transitions_data:
			wf.append("transitions", t)
			
		wf.save(ignore_permissions=True)

	frappe.clear_cache(doctype="Employee Resignation")
