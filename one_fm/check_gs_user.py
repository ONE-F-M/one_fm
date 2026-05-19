import frappe

def run():
    doc = frappe.get_doc("Arrival and Deployment", "ARD-2026-00005")
    print("GS Field Value:", doc.general_services)
    
    if doc.general_services:
        exists = frappe.db.exists("User", doc.general_services)
        print("User exists:", exists)
