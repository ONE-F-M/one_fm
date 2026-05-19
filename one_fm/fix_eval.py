import frappe

def run():
    rules = frappe.get_all("Assignment Rule", filters={"document_type": "Arrival and Deployment"})
    for r in rules:
        doc = frappe.get_doc("Assignment Rule", r.name)
        
        changed = False
        if doc.assign_condition and "doc." in doc.assign_condition:
            doc.assign_condition = doc.assign_condition.replace("doc.", "")
            changed = True
            
        if doc.unassign_condition and "doc." in doc.unassign_condition:
            doc.unassign_condition = doc.unassign_condition.replace("doc.", "")
            changed = True
            
        if changed:
            doc.save(ignore_permissions=True)

    frappe.db.commit()
    print("Fixed safe_eval conditions.")
