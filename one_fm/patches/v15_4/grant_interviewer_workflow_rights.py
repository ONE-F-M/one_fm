import frappe
from frappe.permissions import add_permission

def execute():
    # Attempt to use natively provided add_permission utility if available
    try:
        add_permission("Workflow", "Interviewer", 0)
        frappe.db.commit()
    except Exception:
        # Fallback to direct insertion in Custom DocPerm if add_permission fails
        if not frappe.db.exists("Custom DocPerm", {"parent": "Workflow", "role": "Interviewer"}):
            doc = frappe.new_doc("Custom DocPerm")
            doc.parent = "Workflow"
            doc.parenttype = "DocType"
            doc.parentfield = "permissions"
            doc.role = "Interviewer"
            doc.read = 1
            doc.permlevel = 0
            doc.insert(ignore_permissions=True)
            frappe.db.commit()
