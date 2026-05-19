import frappe

def check_wf():
    wf = frappe.get_all("Workflow", filters={"document_type": "Project Manpower Request", "is_active": 1}, pluck="name")
    if not wf:
        print("No active workflow for PMR.")
        return
    
    doc = frappe.get_doc("Workflow", wf[0])
    for s in doc.states:
        print(f"State: {s.state}, Allow Edit: {s.allow_edit}")

def run():
    check_wf()
