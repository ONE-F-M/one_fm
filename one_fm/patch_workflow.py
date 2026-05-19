import frappe

def run():
    # Update Status Field options in DocType
    doc = frappe.get_doc("DocType", "Arrival and Deployment")
    for df in doc.fields:
        if df.fieldname == "status":
            df.options = "Pending\nArriving\nJoined\nCompleted"
    doc.save(ignore_permissions=True)
    
    # Ensure Workflow Action Master exists
    actions = ["Submit to Logistics", "Mark as Joined"]
    for a in actions:
        if not frappe.db.exists("Workflow Action Master", a):
            frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": a}).insert(ignore_permissions=True)
            
    # Ensure Workflow State exists
    states = ["Pending Logistics", "Joined"]
    for s in states:
        if not frappe.db.exists("Workflow State", s):
            frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": s, "style": "Primary" if s == "Joined" else "Warning"}).insert(ignore_permissions=True)

    frappe.db.commit()

    # Update Workflow
    wf_name = "Arrival and Deployment Workflow"
    if not frappe.db.exists("Workflow", wf_name):
        return
        
    wf = frappe.get_doc("Workflow", wf_name)
    wf.states = []
    wf.transitions = []
    
    # Define States
    wf.append("states", {"state": "Draft", "doc_status": 0, "allow_edit": "Recruitment Manager", "update_field": "status", "update_value": "Pending"})
    wf.append("states", {"state": "Pending Onboarding", "doc_status": 0, "allow_edit": "Onboarding Officer", "update_field": "status", "update_value": "Pending"})
    wf.append("states", {"state": "Pending Logistics", "doc_status": 0, "allow_edit": "General Services", "update_field": "status", "update_value": "Arriving"})
    wf.append("states", {"state": "Joined", "doc_status": 0, "allow_edit": "System Manager", "update_field": "status", "update_value": "Joined"})

    # Define Transitions
    wf.append("transitions", {"state": "Draft", "action": "Submit to Onboarding", "next_state": "Pending Onboarding", "allowed": "Recruitment Manager"})
    wf.append("transitions", {"state": "Pending Onboarding", "action": "Submit to Logistics", "next_state": "Pending Logistics", "allowed": "Onboarding Officer"})
    wf.append("transitions", {"state": "Pending Logistics", "action": "Mark as Joined", "next_state": "Joined", "allowed": "Onboarding Officer"})
    
    wf.save(ignore_permissions=True)
    frappe.db.commit()
    print("Workflow patched.")
