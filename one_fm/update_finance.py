import frappe

def run():
    if frappe.db.exists("Assignment Rule", "Arrival - Assign Finance"):
        doc = frappe.get_doc("Assignment Rule", "Arrival - Assign Finance")
        doc.assign_condition = "doc.workflow_state == 'Pending Support Departments' and doc.candidate_country_process"
        doc.save(ignore_permissions=True)
        frappe.db.commit()
        print("Finance assignment rule updated for overseas only.")
