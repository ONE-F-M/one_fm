import frappe

def execute():
    # Query builder approach or bulk set_value
    # Since frappe.db.set_value handles updates efficiently without loading the document
    frappe.db.set_value(
        "Client Event",
        {"workflow_state": "Pending Approval"},
        "workflow_state",
        "Pending Operations Manager",
        update_modified=False
    )
    
    # Also update any Event Staff records if their conditions were affected, but just updating Client Event is requested.
