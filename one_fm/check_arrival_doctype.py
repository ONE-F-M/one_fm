import frappe

def check_doctype():
    exists = frappe.db.exists("DocType", "Arrival and Deployment")
    print(f"Arrival and Deployment exists: {exists}")

def run():
    check_doctype()
