import frappe

def create_roles():
    roles = ["Transportation Manager", "General Services", "Finance"]
    for role in roles:
        if not frappe.db.exists("Role", role):
            frappe.get_doc({
                "doctype": "Role",
                "role_name": role
            }).insert(ignore_permissions=True)
            print(f"Created role {role}")

def create_workflow():
    wf_name = "Arrival and Deployment Workflow"
    if frappe.db.exists("Workflow", wf_name):
        frappe.delete_doc("Workflow", wf_name, ignore_permissions=True)
        
    wf = frappe.new_doc("Workflow")
    wf.workflow_name = wf_name
    wf.document_type = "Arrival and Deployment"
    wf.is_active = 1
    
    # States
    wf.append("states", {
        "state": "Draft",
        "doc_status": 0,
        "allow_edit": "Recruiter",
        "update_field": "status",
        "update_value": "Pending"
    })
    wf.append("states", {
        "state": "Pending Onboarding",
        "doc_status": 0,
        "allow_edit": "Onboarding Officer",
        "update_field": "status",
        "update_value": "Pending"
    })
    wf.append("states", {
        "state": "Pending Logistics and Finance",
        "doc_status": 0,
        "allow_edit": "General Services",
        "update_field": "status",
        "update_value": "Arriving"
    })
    wf.append("states", {
        "state": "Completed",
        "doc_status": 0,
        "allow_edit": "System Manager",
        "update_field": "status",
        "update_value": "Completed"
    })
    
    # Transitions
    wf.append("transitions", {
        "state": "Draft",
        "action": "Submit to Onboarding",
        "next_state": "Pending Onboarding",
        "allowed": "Recruiter"
    })
    wf.append("transitions", {
        "state": "Pending Onboarding",
        "action": "Submit to Logistics & Finance",
        "next_state": "Pending Logistics and Finance",
        "allowed": "Onboarding Officer"
    })
    wf.append("transitions", {
        "state": "Pending Logistics and Finance",
        "action": "Complete Deployment",
        "next_state": "Completed",
        "allowed": "General Services"
    })
    # allow transport and finance to also complete it
    wf.append("transitions", {
        "state": "Pending Logistics and Finance",
        "action": "Complete Deployment",
        "next_state": "Completed",
        "allowed": "Transportation Manager"
    })
    wf.append("transitions", {
        "state": "Pending Logistics and Finance",
        "action": "Complete Deployment",
        "next_state": "Completed",
        "allowed": "Finance"
    })
    
    wf.insert(ignore_permissions=True)
    print(f"Created workflow {wf_name}")

frappe.init(site="onefm.local")
frappe.connect()
create_roles()
create_workflow()
frappe.db.commit()
