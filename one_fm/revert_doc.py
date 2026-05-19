import frappe

def run():
    docname = "ARD-2026-00005"
    if not frappe.db.exists("Arrival and Deployment", docname):
        return
        
    # Revert state
    frappe.db.set_value("Arrival and Deployment", docname, "workflow_state", "Pending Onboarding")
    
    # Delete ToDos associated with it to reset assignments
    todos = frappe.get_all("ToDo", filters={'reference_type': 'Arrival and Deployment', 'reference_name': docname})
    for t in todos:
        frappe.delete_doc("ToDo", t.name, ignore_permissions=True)
        
    frappe.db.commit()
    print("Reverted to Pending Onboarding.")
