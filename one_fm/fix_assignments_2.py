import frappe

def run():
    # Revert General Services assignment to trigger for both Local and Overseas
    if frappe.db.exists("Assignment Rule", "Arrival - Assign General Services"):
        doc = frappe.get_doc("Assignment Rule", "Arrival - Assign General Services")
        doc.assign_condition = "doc.workflow_state == 'Pending Support Departments'"
        doc.save(ignore_permissions=True)

    frappe.db.commit()
    print("GS Assignment rule updated to trigger for both.")
