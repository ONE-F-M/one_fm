import frappe
import json

def run():
    doc = frappe.get_doc("Workflow", "Arrival and Deployment Workflow")
    for s in doc.states:
        print(f"State: {s.state}, Update Field: {s.update_field}, Update Value: {s.update_value}")
