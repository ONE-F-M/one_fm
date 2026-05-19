import frappe

def run():
    rules = frappe.get_all("Assignment Rule", filters={"document_type": "Arrival and Deployment"})
    for r in rules:
        doc = frappe.get_doc("Assignment Rule", r.name)
        print(f"Rule: {r.name}")
        print(f"Condition: {doc.assign_condition}")
        print(f"Disabled: {doc.disabled}")
        print("---")
