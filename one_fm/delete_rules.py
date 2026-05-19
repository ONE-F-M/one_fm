import frappe

def run():
    # 1. Delete the Assignment Rules because they conflict and only one triggers
    rules = ["Arrival - Assign Finance", "Arrival - Assign General Services", "Arrival - Assign Transportation", "Arrival - Assign Warehouse", "Arrival - Recruiter Not Arrived"]
    for r in rules:
        if frappe.db.exists("Assignment Rule", r):
            frappe.delete_doc("Assignment Rule", r, ignore_permissions=True)
            
    frappe.db.commit()
    print("Deleted built-in assignment rules to replace with custom logic.")
