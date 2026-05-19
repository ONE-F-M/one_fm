import frappe

def check_arrival():
    docs = frappe.get_all("DocType", filters={"name": ["like", "%Arrival%"]}, fields=["name"])
    print(f"Arrival DocTypes: {docs}")

def run():
    check_arrival()
