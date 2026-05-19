import frappe

def run():
    # Ensure Roles exist
    roles = ["Transportation", "General Services", "Onboarding Officer", "Recruitment Manager"]
    for role in roles:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)

    wf_name = "Arrival and Deployment Workflow"
    if not frappe.db.exists("Workflow", wf_name):
        return
        
    # Add Missing Actions & States
    actions = ["Submit to Support Departments", "Mark as Joined", "Did Not Arrive"]
    for a in actions:
        if not frappe.db.exists("Workflow Action Master", a):
            frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": a}).insert(ignore_permissions=True)
            
    states = ["Pending Support Departments", "Did Not Arrive"]
    for s in states:
        if not frappe.db.exists("Workflow State", s):
            frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": s, "style": "Danger" if s == "Did Not Arrive" else "Warning"}).insert(ignore_permissions=True)
            
    wf = frappe.get_doc("Workflow", wf_name)
    wf.states = []
    wf.transitions = []
    
    # States
    wf.append("states", {"state": "Draft", "doc_status": 0, "allow_edit": "Recruitment Manager", "update_field": "status", "update_value": "Pending"})
    wf.append("states", {"state": "Pending Onboarding", "doc_status": 0, "allow_edit": "Onboarding Officer", "update_field": "status", "update_value": "Pending"})
    wf.append("states", {"state": "Pending Support Departments", "doc_status": 0, "allow_edit": "System Manager", "update_field": "status", "update_value": "Arriving"})
    wf.append("states", {"state": "Joined", "doc_status": 0, "allow_edit": "System Manager", "update_field": "status", "update_value": "Joined"})
    wf.append("states", {"state": "Did Not Arrive", "doc_status": 0, "allow_edit": "System Manager", "update_field": "status", "update_value": "Pending"})

    # Transitions
    wf.append("transitions", {"state": "Draft", "action": "Submit to Onboarding", "next_state": "Pending Onboarding", "allowed": "Recruitment Manager"})
    wf.append("transitions", {"state": "Pending Onboarding", "action": "Submit to Support Departments", "next_state": "Pending Support Departments", "allowed": "Onboarding Officer"})
    
    wf.append("transitions", {"state": "Pending Support Departments", "action": "Mark as Joined", "next_state": "Joined", "allowed": "Transportation"})
    wf.append("transitions", {"state": "Pending Support Departments", "action": "Mark as Joined", "next_state": "Joined", "allowed": "General Services"})
    
    wf.append("transitions", {"state": "Pending Support Departments", "action": "Did Not Arrive", "next_state": "Did Not Arrive", "allowed": "Transportation"})
    wf.append("transitions", {"state": "Pending Support Departments", "action": "Did Not Arrive", "next_state": "Did Not Arrive", "allowed": "General Services"})
    
    wf.save(ignore_permissions=True)
    frappe.db.commit()
    print("Workflow fixed.")
