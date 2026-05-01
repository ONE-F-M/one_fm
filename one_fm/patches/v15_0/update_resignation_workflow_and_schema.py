import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
	# 1. Add operations_manager to Operations Site
	create_custom_fields({
		"Operations Site": [
			{
				"fieldname": "operations_manager",
				"label": "Operations Manager",
				"fieldtype": "Link",
				"options": "User",
				"insert_after": "site_supervisor_name"
			}
		]
	})

	# 3. Update Workflow for Employee Resignation
	workflow_name = "Employee Resignation"
	
	new_states = {"Draft": "Primary", "Pending Offboarding Officer": "Warning", "Pending Relieving Date Correction": "Danger", "Pending Supervisor": "Warning", "Pending Operations Manager": "Warning", "Approved": "Success", "Withdrawn": "Inverse"}
	for state, style in new_states.items():
		if not frappe.db.exists("Workflow State", state):
			frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state, "style": style}).insert(ignore_permissions=True)
			
	new_actions = ["Submit to Offboarding Officer", "Review Completed", "Submit for Review", "Request Relieving Date Change", "Resubmit Date", "Approve"]
	for action in new_actions:
		if not frappe.db.exists("Workflow Action Master", action):
			frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action}).insert(ignore_permissions=True)
	
	if frappe.db.exists("Workflow", workflow_name):
		wf = frappe.get_doc("Workflow", workflow_name)
		# Rebuild states natively
		wf.set("states", [])
		wf.set("transitions", [])
		
		states_data = [
			{"state": "Draft", "doc_status": 0, "update_field": "status", "update_value": "Pending", "allow_edit": "Employee", "style": "Primary"},
			{"state": "Pending Offboarding Officer", "doc_status": 0, "update_field": "status", "update_value": "Pending", "allow_edit": "Offboarding Officer", "style": "Warning"},
			{"state": "Pending Supervisor", "doc_status": 0, "update_field": "status", "update_value": "Pending", "allow_edit": "Employee", "style": "Warning"},
			{"state": "Pending Relieving Date Correction", "doc_status": 0, "update_field": "status", "update_value": "Pending", "allow_edit": "Employee", "style": "Danger"},
			{"state": "Pending Operations Manager", "doc_status": 0, "update_field": "status", "update_value": "Pending", "allow_edit": "Operations Manager", "style": "Warning"},
			{"state": "Approved", "doc_status": 1, "update_field": "status", "update_value": "Approved", "allow_edit": "Offboarding Officer", "style": "Success"},
			{"state": "Withdrawn", "doc_status": 1, "update_field": "status", "update_value": "Withdrawn", "allow_edit": "System Manager", "style": "Inverse"}
		]
		for s in states_data:
			wf.append("states", s)
			
		transitions_data = [
			{"state": "Draft", "action": "Submit to Offboarding Officer", "next_state": "Pending Offboarding Officer", "allowed": "Employee"},
			{"state": "Pending Offboarding Officer", "action": "Review Completed", "next_state": "Pending Supervisor", "allowed": "Offboarding Officer"},
			{"state": "Pending Supervisor", "action": "Submit for Review", "next_state": "Pending Operations Manager", "allowed": "Employee", "allowed_user_field": "supervisor"},
			{"state": "Pending Supervisor", "action": "Request Relieving Date Change", "next_state": "Pending Relieving Date Correction", "allowed": "Employee", "allowed_user_field": "supervisor"},
			{"state": "Pending Relieving Date Correction", "action": "Resubmit Date", "next_state": "Pending Supervisor", "allowed": "Employee"},
			{"state": "Pending Operations Manager", "action": "Approve", "next_state": "Approved", "allowed": "Operations Manager"}
		]
		for t in transitions_data:
			wf.append("transitions", t)
			
		wf.save(ignore_permissions=True)

	# 4. Create/Update Assignment Rules
	assignment_rules = [
		{
			"name": "Resignation - Pending Offboarding Officer",
			"document_type": "Employee Resignation",
			"description": "Please review this resignation as Offboarding Officer.",
			"assign_condition": "doc.workflow_state == 'Pending Offboarding Officer'",
			"unassign_condition": "doc.workflow_state != 'Pending Offboarding Officer'",
			"rule": "Round Robin",
			"assign_to_role": "Offboarding Officer"
		},
		{
			"name": "Resignation - Pending Supervisor",
			"document_type": "Employee Resignation",
			"description": "Please review the Resignation and Relieving date.",
			"assign_condition": "doc.workflow_state == 'Pending Supervisor'",
			"unassign_condition": "doc.workflow_state != 'Pending Supervisor'",
			"rule": "Based on Field",
			"field": "supervisor",
			"assign_to": []
		},
		{
			"name": "Resignation - Pending Operations Manager",
			"document_type": "Employee Resignation",
			"description": "Please review and approve this Resignation.",
			"assign_condition": "doc.workflow_state == 'Pending Operations Manager'",
			"unassign_condition": "doc.workflow_state != 'Pending Operations Manager'",
			"rule": "Based on Field",
			"field": "operations_manager",
			"assign_to": []
		},
		{
			"name": "Resignation - Relieving Date Correction",
			"document_type": "Employee Resignation",
			"description": "Your supervisor has requested an adjustment to your Relieving Date.",
			"assign_condition": "doc.workflow_state == 'Pending Relieving Date Correction'",
			"unassign_condition": "doc.workflow_state != 'Pending Relieving Date Correction'",
			"rule": "Based on Field",
			"field": "owner",
			"assign_to": []
		}
	]
	
	for ar in assignment_rules:
		target_name = ar["name"]
		if not frappe.db.exists("Assignment Rule", target_name):
			doc = frappe.new_doc("Assignment Rule")
			doc.update(ar)
			
			for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
				doc.append("assignment_days", {"day": day})
				
			if "assign_to_role" in ar and ar["assign_to_role"]:
				users_with_role = frappe.get_all("Has Role", filters={"role": ar["assign_to_role"]}, fields=["parent"])
				for u in users_with_role:
					doc.append("users", {"user": u.parent})
			elif "assign_to" in ar and ar["assign_to"]:
				for u in ar["assign_to"]:
					doc.append("users", {"user": u})
					
			doc.is_assignment_rule_with_workflow = 1
			try:
				doc.insert(ignore_permissions=True)
			except Exception as e:
				frappe.log_error(
					message=frappe.get_traceback(),
					title=f"Assignment Rule Creation Failed: {target_name}"
				)
		else:
			doc = frappe.get_doc("Assignment Rule", target_name)
			try:
				doc_dict = {k:v for k,v in ar.items() if k not in ("name", "assign_to", "assign_to_role")}
				doc.update(doc_dict)
				doc.save(ignore_permissions=True)
			except Exception as e:
				frappe.log_error(
					message=frappe.get_traceback(),
					title=f"Assignment Rule Update Failed: {target_name}"
				)
