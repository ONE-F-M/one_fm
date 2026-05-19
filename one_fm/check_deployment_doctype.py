import frappe

def check_deployment():
    docs = frappe.get_all("DocType", filters={"name": ["like", "%Deployment%"]}, fields=["name"])
    print(f"Deployment DocTypes: {docs}")

def run():
    check_deployment()
